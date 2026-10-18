"""Which readouts expose which defects? TSMC 65 nm main data (60,000 independent neurons, 4 stimuli each), die-based split,
threshold at 1 % false reject of healthy validation neurons, miss rate on test dies. Mean over 6 random die splits."""
import sys, warnings, time
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
t0 = time.time()
d = pd.read_csv("data/tsmc65/readouts.csv.gz", low_memory=False)
d = d[(d.kind == "main") & (d.is_nominal == 0)].copy()
d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1
SPIKE = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]; ANALOG = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]
SUP = ["qdd_all", "qdd_sp", "ipk"]; NODE = ["tail_t", "n3_t", "mid_t", "n4_t", "n3min", "midpk", "tailmax", "tailmin", "n4pk"]
d["neuron"] = d.deck + "_r" + d.mc_run.astype(str)
w = d.pivot_table(index=["neuron", "die", "corner", "defect_id"], columns="stim_nA", values=SPIKE + ANALOG + SUP + NODE, aggfunc="first")
w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]; w = w.reset_index()
print("neurons", len(w), "healthy", (w.defect_id == "healthy").sum(), "dies", w["die"].nunique(), "(%.0fs)" % (time.time() - t0), flush=True)
def cols(fs): return [c for c in w.columns if "@" in c and c.split("@")[0] in fs]
sets = [("spike", SPIKE), ("spike+analog (Vm)", SPIKE + ANALOG), ("spike+analog+supply", SPIKE + ANALOG + SUP),
        ("spike+analog+supply+nodes", SPIKE + ANALOG + SUP + NODE), ("supply only", SUP)]
y = (w.defect_id != "healthy").astype(int).values; did = w.defect_id.values
dies = np.array(sorted(w["die"].unique())); res = {n: {} for n, _ in sets}; allmiss = {n: [] for n, _ in sets}
for seed in range(6):
    dd = dies.copy(); np.random.default_rng(100 + seed).shuffle(dd); ntr, nva = int(.6 * len(dd)), int(.2 * len(dd))
    sp = {x: 0 for x in dd[:ntr]}; sp.update({x: 1 for x in dd[ntr:ntr + nva]}); sp.update({x: 2 for x in dd[ntr + nva:]})
    s = w["die"].map(sp).values; tr, va, te = s == 0, s == 1, s == 2
    for nm, fs in sets:
        X = w[cols(fs)].to_numpy(float)
        m = HistGradientBoostingClassifier(max_iter=150, learning_rate=.1, max_leaf_nodes=31, early_stopping=False, random_state=0).fit(X[tr], y[tr])
        p = np.clip(m.predict_proba(X)[:, 1], 1e-6, 1 - 1e-6); sc = np.log(p / (1 - p)); thr = np.quantile(sc[va & (y == 0)], .99)
        allmiss[nm].append((sc[te & (y == 1)] <= thr).mean() * 100)
        for k in set(did) - {"healthy"}:
            res[nm].setdefault(k, []).append((sc[te & (did == k)] <= thr).mean() * 100)
    print("split", seed, "done (%.0fs)" % (time.time() - t0), flush=True)
print("\n=== Missed faulty neurons at 1% false reject (mean +- sd over 6 die splits; all 46 defects pooled) ===")
for nm, _ in sets: print("  %-28s %5.1f +- %.1f %%" % (nm, np.mean(allmiss[nm]), np.std(allmiss[nm])))
T = pd.DataFrame({nm: pd.Series({k: np.mean(v) for k, v in res[nm].items()}) for nm, _ in sets})
T.to_csv("results/tsmc65_miss_rate_per_defect.csv")
print("\n=== Defects still missed > 5% (per defect, %) ===")
pd.set_option("display.width", 160)
bad = T[(T > 5).any(axis=1)].sort_values(sets[1][0], ascending=False)
print(bad.round(1).to_string())
print("\ndefects missed >5%% : spike %d | +analog %d | +supply %d | +nodes %d" % tuple((T[n] > 5).sum() for n, _ in sets[:4]))
