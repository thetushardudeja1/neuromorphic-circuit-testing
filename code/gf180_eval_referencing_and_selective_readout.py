"""Patent pipeline on the GF180 dataset, evaluated with a train/val/test split BY DIE.

P1 spike features, raw                       (spike-only test, no referencing)
P2 spike features, neighbour-referenced      (die-level shift removed)
P3 spike + analog readouts, referenced, for ALL neurons          (upper bound)
P4 selective: P2 for everyone; the ~20% least confident neurons also get the analog readout (P3), fused
Metrics: miss rate of faulty neurons at 1% false reject of healthy neurons (threshold set on validation dies),
         and defect-location accuracy (46 classes) on test dies.
Neighbour context for each neuron (same die, itself excluded): 11 random healthy + 4 random defective neurons.
"""
import sys, warnings, time
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
t00 = time.time()
SNAP = sys.argv[1] if len(sys.argv) > 1 else "data/gf180/readouts.csv.gz"
rng = np.random.default_rng(0)

df = pd.read_csv(SNAP)
df = df[df.kind == "main"].drop_duplicates(["task", "stim_nA"]).copy()
df["lat"] = df.t1 - 5e-6
df["per"] = df.t2 - df.t1
df["width"] = df.tf1 - df.t1
SPIKE = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]
ANALOG = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]
w = df.pivot_table(index=["task", "die", "corner", "defect_id"], columns="stim_nA", values=SPIKE + ANALOG, aggfunc="first")
w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]
w = w.reset_index()
cs = [c for c in w.columns if c.split("@")[0] in SPIKE and "@" in c]
ca = [c for c in w.columns if c.split("@")[0] in ANALOG and "@" in c]
w["faulty"] = (w.defect_id != "healthy").astype(int)
print("neurons %d (healthy %d, faulty %d), dies %d, features: spike %d, analog %d" % (len(w), (w.faulty == 0).sum(), w.faulty.sum(), w["die"].nunique(), len(cs), len(ca)), flush=True)

# ---- neighbour referencing (per neuron: 11 healthy + 4 defective other neurons of the same die)
X = w[cs + ca].to_numpy(float)
ref = np.full_like(X, np.nan)
for die, idx in w.groupby("die").groups.items():
    idx = np.asarray(list(idx)); healthy = idx[w.faulty.values[idx] == 0]; faulty = idx[w.faulty.values[idx] == 1]
    for i in idx:
        hh = healthy[healthy != i]; ff = faulty[faulty != i]
        nb = np.concatenate([rng.choice(hh, min(11, len(hh)), replace=False), rng.choice(ff, min(4, len(ff)), replace=False)])
        med = np.nanmedian(X[nb], axis=0)                     # median over VALID entries only
        ref[i] = X[i] - med                                   # invalid (NaN) entries stay NaN: placeholders are not shifted
Rs, Ra = ref[:, :len(cs)], ref[:, len(cs):]
Xs, Xa = X[:, :len(cs)], X[:, len(cs):]

# ---- split by die
dies = np.array(sorted(w["die"].unique())); rng.shuffle(dies)
ntr, nva = int(0.6 * len(dies)), int(0.2 * len(dies))
split = {d: "train" for d in dies[:ntr]}; split.update({d: "val" for d in dies[ntr:ntr + nva]}); split.update({d: "test" for d in dies[ntr + nva:]})
sp = w["die"].map(split).values
tr, va, te = sp == "train", sp == "val", sp == "test"
y = w.faulty.values
print("split by die: train %d dies / val %d / test %d ; neurons %d / %d / %d" % (ntr, nva, len(dies) - ntr - nva, tr.sum(), va.sum(), te.sum()), flush=True)

def hgb(n_iter=150, **kw):
    return HistGradientBoostingClassifier(max_iter=n_iter, learning_rate=0.1, max_leaf_nodes=31, early_stopping=False, random_state=0, **kw)

def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6); return np.log(p / (1 - p))

sets = {"P1 spike raw": Xs, "P2 spike referenced": Rs, "P3 spike+analog referenced": np.hstack([Rs, Ra])}
score = {}
for name, M in sets.items():
    m = hgb().fit(M[tr], y[tr]); score[name] = logit(m.predict_proba(M)[:, 1])
    print("trained", name, "(%.0fs)" % (time.time() - t00), flush=True)

def miss_at_1pct(s, thr_from_val=True):
    thr = np.quantile(s[va & (y == 0)], 0.99)
    fr = (s[te & (y == 0)] > thr).mean()
    miss = (s[te & (y == 1)] <= thr).mean()
    return thr, fr, miss

# ---- P4: selective acquisition (about 20% of neurons at a realistic 25% fault prevalence)
s2, s3 = score["P2 spike referenced"], score["P3 spike+analog referenced"]
thr2 = np.quantile(s2[va & (y == 0)], 0.99)
dist = np.abs(s2 - thr2)
wt = np.where(y == 0, 0.75 / (y == 0)[va].sum(), 0.25 / (y == 1)[va].sum())            # reweight validation to 25% faulty
order = np.argsort(dist[va]); cum = np.cumsum(wt[va][order]); d_star = dist[va][order][np.searchsorted(cum, 0.20)]
sel = dist <= d_star
fused = np.where(sel, 0.5 * (s2 + s3), s2)                                               # geometric-mean fusion of the two posteriors
score["P4 selective (20% readout)"] = fused
wt_te = np.where(y == 0, 0.75 / (y == 0)[te].sum(), 0.25 / (y == 1)[te].sum())[te]
frac_sel_test = wt_te[sel[te]].sum()

print("\n=== Detection: miss rate of faulty neurons at 1%% false reject (thresholds from validation dies; results on %d test-die neurons) ===" % te.sum())
rows = []
for name in ["P1 spike raw", "P2 spike referenced", "P3 spike+analog referenced", "P4 selective (20% readout)"]:
    thr, fr, miss = miss_at_1pct(score[name]); rows.append((name, fr, miss))
    print("  %-28s miss rate %5.1f %%   (actual false reject on test %.1f %%)" % (name, 100 * miss, 100 * fr))
print("  P4: analog readout acquired for %.1f%% of neurons (at 25%% fault prevalence), %.1f%% of all test neurons at this die mix" % (100 * frac_sel_test, 100 * sel[te].mean()))

# ---- per-defect miss rates (test dies)
print("\n=== Per-defect miss rate at 1%% false reject (test dies): spike-raw -> referenced -> +analog (all) -> selective ===")
tab = []
for did in sorted(set(w.defect_id) - {"healthy"}):
    m_ = te & (w.defect_id.values == did)
    r = []
    for name in ["P1 spike raw", "P2 spike referenced", "P3 spike+analog referenced", "P4 selective (20% readout)"]:
        thr = np.quantile(score[name][va & (y == 0)], 0.99); r.append((score[name][m_] <= thr).mean() * 100)
    tab.append((did, m_.sum(), *r))
T = pd.DataFrame(tab, columns=["defect", "n", "P1", "P2", "P3", "P4"]).set_index("defect")
pd.set_option("display.width", 140); pd.set_option("display.max_rows", 100)
print(T.round(0).astype(int).sort_values("P2", ascending=False).head(22).to_string())
print("defects with P2 miss > 50%%: %d ; of which P3 miss < 50%%: %d ; P4 miss < 50%%: %d" % ((T.P2 > 50).sum(), ((T.P2 > 50) & (T.P3 < 50)).sum(), ((T.P2 > 50) & (T.P4 < 50)).sum()))

# ---- defect-location classification among truly faulty neurons
print("\n=== Defect-location accuracy (46 classes, faulty test neurons) ===")
fm = {n: (w.faulty.values == 1) for n in ["tr", "te"]}
trf, tef = tr & (y == 1), te & (y == 1)
cls = w.defect_id.values
res = {}
for name, M in [("P2 spike referenced", Rs), ("P3 spike+analog referenced", np.hstack([Rs, Ra]))]:
    m = HistGradientBoostingClassifier(max_iter=60, learning_rate=0.15, max_leaf_nodes=15, early_stopping=False, random_state=0).fit(M[trf], cls[trf])
    P = m.predict_proba(M[tef]); res[name] = (m.classes_, P)
    print("  %-28s top-1 %.1f %%   top-3 %.1f %%   (%.0fs)" % (name, 100 * (m.classes_[P.argmax(1)] == cls[tef]).mean(), 100 * np.mean([cls[tef][i] in m.classes_[np.argsort(-P[i])[:3]] for i in range(len(P))]), time.time() - t00), flush=True)
c2, P2_ = res["P2 spike referenced"]; c3, P3_ = res["P3 spike+analog referenced"]
selte = sel[tef]
Pf = np.where(selte[:, None], np.sqrt(P2_ * P3_) / np.sqrt(P2_ * P3_).sum(1, keepdims=True), P2_)
print("  %-28s top-1 %.1f %%   (analog readout for %.0f%% of these)" % ("P4 selective", 100 * (c2[Pf.argmax(1)] == cls[tef]).mean(), 100 * selte.mean()))
print("\ndone in %.0f s" % (time.time() - t00))
