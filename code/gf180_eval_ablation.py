"""Ablation: what do neighbour referencing and the analog readouts each contribute? (same split, same 1% false-reject rule)"""
import sys, warnings, time
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
rng = np.random.default_rng(0)
df = pd.read_csv("data/gf180/readouts.csv.gz"); df = df[df.kind == "main"].drop_duplicates(["task", "stim_nA"]).copy()
df["lat"] = df.t1 - 5e-6; df["per"] = df.t2 - df.t1; df["width"] = df.tf1 - df.t1
SPIKE = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]; ANALOG = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]
w = df.pivot_table(index=["task", "die", "corner", "defect_id"], columns="stim_nA", values=SPIKE + ANALOG, aggfunc="first")
w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]; w = w.reset_index()
cs = [c for c in w.columns if c.split("@")[0] in SPIKE and "@" in c]; ca = [c for c in w.columns if c.split("@")[0] in ANALOG and "@" in c]
w["faulty"] = (w.defect_id != "healthy").astype(int); y = w.faulty.values
X = w[cs + ca].to_numpy(float); n_s = len(cs)

def reference(n_h, n_f):
    ref = np.full_like(X, np.nan); med_all = np.full_like(X, np.nan)
    for die, idx in w.groupby("die").groups.items():
        idx = np.asarray(list(idx)); healthy = idx[y[idx] == 0]; faulty = idx[y[idx] == 1]
        for i in idx:
            hh = healthy[healthy != i]; ff = faulty[faulty != i]
            nb = np.concatenate([rng.choice(hh, min(n_h, len(hh)), replace=False), rng.choice(ff, min(n_f, len(ff)), replace=False)]) if n_f else rng.choice(hh, min(n_h, len(hh)), replace=False)
            m = np.nanmedian(X[nb], axis=0); med_all[i] = m; ref[i] = X[i] - m
    return ref, med_all
R_real, M_real = reference(11, 4)      # realistic: 27% faulty neighbours
R_orac, M_orac = reference(15, 0)      # oracle: all 15 neighbours healthy
dies = np.array(sorted(w["die"].unique())); np.random.default_rng(0).shuffle(dies)
ntr, nva = int(0.6 * len(dies)), int(0.2 * len(dies)); sp = {d: "train" for d in dies[:ntr]}; sp.update({d: "val" for d in dies[ntr:ntr + nva]}); sp.update({d: "test" for d in dies[ntr + nva:]})
s = w["die"].map(sp).values; tr, va, te = s == "train", s == "val", s == "test"
S, A = slice(0, n_s), slice(n_s, None)
def run(name, M):
    m = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.1, max_leaf_nodes=31, early_stopping=False, random_state=0).fit(M[tr], y[tr])
    p = np.clip(m.predict_proba(M)[:, 1], 1e-6, 1 - 1e-6); sc = np.log(p / (1 - p))
    thr = np.quantile(sc[va & (y == 0)], 0.99)
    print("  %-52s miss %5.1f %%   (false reject on test %.1f %%)" % (name, 100 * (sc[te & (y == 1)] <= thr).mean(), 100 * (sc[te & (y == 0)] > thr).mean()), flush=True)
print("ablation, miss rate of faulty test neurons at 1% false reject")
run("spike raw", X[:, S])
run("spike referenced (27% faulty neighbours)", R_real[:, S])
run("spike referenced (oracle: all-healthy neighbours)", R_orac[:, S])
run("spike raw + neighbour median as extra features", np.hstack([X[:, S], M_real[:, S]]))
run("analog raw only", X[:, A])
run("analog referenced only", R_real[:, A])
run("spike raw + analog raw", X)
run("spike raw + analog referenced", np.hstack([X[:, S], R_real[:, A]]))
run("spike ref + analog ref", R_real)
run("spike ref + analog ref (oracle neighbours)", R_orac)
run("spike+analog raw + neighbour medians as features", np.hstack([X, M_real]))
