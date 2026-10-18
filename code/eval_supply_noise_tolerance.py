"""Tolerance of the supply-current readout to measurement noise (TSMC 65 nm, all 46 defects, die-based split, 1 % false reject).
Relative Gaussian noise is added to every supply value (qdd_all, qdd_sp, ipk at 4 stimuli) of ALL neurons (train and test) after simulation."""
import warnings, time
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
d = pd.read_csv("data/tsmc65/readouts.csv.gz", low_memory=False)
d = d[(d.kind == "main") & (d.is_nominal == 0)].copy()
d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1
SPIKE = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]; ANALOG = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]; SUP = ["qdd_all", "qdd_sp", "ipk"]
d["neuron"] = d.deck + "_r" + d.mc_run.astype(str)
w = d.pivot_table(index=["neuron", "die", "defect_id"], columns="stim_nA", values=SPIKE + ANALOG + SUP, aggfunc="first")
w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]; w = w.reset_index()
base = [c for c in w.columns if "@" in c and c.split("@")[0] in SPIKE + ANALOG]; sup = [c for c in w.columns if "@" in c and c.split("@")[0] in SUP]
y = (w.defect_id != "healthy").astype(int).values; did = w.defect_id.values
dies = np.array(sorted(w["die"].unique())); rng = np.random.default_rng(5)
print("relative noise on supply readouts | missed faulty %% at 1%% FR (mean+-sd of 3 splits) | defects still missed >5%%")
for rel in [0, 0.005, 0.01, 0.02, 0.05, 0.10]:
    allm, bad = [], {}
    S = w[sup].to_numpy(float); S = S * (1 + rel * rng.standard_normal(S.shape)); X = np.hstack([w[base].to_numpy(float), S])
    for seed in range(3):
        dd = dies.copy(); np.random.default_rng(100 + seed).shuffle(dd); ntr, nva = int(.6 * len(dd)), int(.2 * len(dd))
        sp = {x: 0 for x in dd[:ntr]}; sp.update({x: 1 for x in dd[ntr:ntr + nva]}); sp.update({x: 2 for x in dd[ntr + nva:]})
        s = w["die"].map(sp).values; tr, va, te = s == 0, s == 1, s == 2
        m = HistGradientBoostingClassifier(max_iter=150, learning_rate=.1, max_leaf_nodes=31, early_stopping=False, random_state=0).fit(X[tr], y[tr])
        p = np.clip(m.predict_proba(X)[:, 1], 1e-6, 1 - 1e-6); sc = np.log(p / (1 - p)); thr = np.quantile(sc[va & (y == 0)], .99)
        allm.append((sc[te & (y == 1)] <= thr).mean() * 100)
        for k in set(did) - {"healthy"}: bad.setdefault(k, []).append((sc[te & (did == k)] <= thr).mean() * 100)
    worst = sorted(((np.mean(v), k) for k, v in bad.items() if np.mean(v) > 5), reverse=True)
    print("  %5.1f %%   | %5.1f +- %.1f | %d  %s" % (rel * 100, np.mean(allm), np.std(allm), len(worst), ", ".join("%s %.0f" % (k, v) for v, k in worst[:6])), flush=True)
