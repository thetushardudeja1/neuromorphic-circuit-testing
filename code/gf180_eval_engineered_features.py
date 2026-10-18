import warnings, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
df = pd.read_csv("data/gf180/readouts.csv.gz"); df = df[df.kind == "main"].drop_duplicates(["task", "stim_nA"]).copy()
df["lat"] = df.t1 - 5e-6; df["per"] = df.t2 - df.t1; df["width"] = df.tf1 - df.t1
SPIKE = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]; ANALOG = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]
w = df.pivot_table(index=["task", "die", "corner", "defect_id"], columns="stim_nA", values=SPIKE + ANALOG, aggfunc="first")
w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]; w = w.reset_index()
base = [c for c in w.columns if "@" in c]
E = {}
S = [50, 100, 200, 400]
for f in ["lat", "per", "width", "tcmp", "ttrip", "t6"]:
    for a, b in [(50, 100), (100, 200), (200, 400), (50, 400)]:
        E["r_%s_%d_%d" % (f, a, b)] = np.log(w["%s@%d" % (f, a)].abs() + 1e-12) - np.log(w["%s@%d" % (f, b)].abs() + 1e-12)
for s in S:
    E["q@%d" % s] = w["lat@%d" % s] * s * 1e-9           # charge to trip ~ C*dV
    E["cmpfrac@%d" % s] = w["tcmp@%d" % s] / (w["per@%d" % s] + 1e-12)
    E["dv@%d" % s] = w["vpk@%d" % s] - w["vtrip@%d" % s]
    E["dr@%d" % s] = w["vtrip@%d" % s] - w["vrst@%d" % s]
    E["swing@%d" % s] = w["vpk@%d" % s] - w["vmin@%d" % s]
# linear fit lat vs 1/I : intercept (fixed delay) and slope (C dV)
inv = np.array([1 / s for s in S]); L = np.stack([w["lat@%d" % s].values for s in S], 1)
ok = np.isfinite(L).all(1); sl = np.full(len(w), np.nan); ic = sl.copy(); rs = sl.copy()
A = np.vstack([inv, np.ones(4)]).T
co = np.linalg.lstsq(A, L[ok].T, rcond=None)[0]; sl[ok], ic[ok] = co[0], co[1]; rs[ok] = np.abs(L[ok] - (A @ co).T).mean(1)
E["fit_slope"], E["fit_icpt"], E["fit_res"] = sl, ic, rs
Ef = pd.DataFrame(E); y = (w.defect_id != "healthy").astype(int).values
Xb = w[base].to_numpy(float); Xe = np.hstack([Xb, Ef.to_numpy(float)])
dies = np.array(sorted(w["die"].unique())); HID = ["mna_on", "mn2_off", "mna_off", "mn3_off"]
res = {k: {h: [] for h in HID + ["ALL"]} for k in ["base", "eng"]}
for seed in range(6):
    d = dies.copy(); np.random.default_rng(100 + seed).shuffle(d); ntr, nva = int(.6*len(d)), int(.2*len(d))
    sp = {x: 0 for x in d[:ntr]}; sp.update({x: 1 for x in d[ntr:ntr+nva]}); sp.update({x: 2 for x in d[ntr+nva:]})
    s = w["die"].map(sp).values
    for nm, X in [("base", Xb), ("eng", Xe)]:
        m = HistGradientBoostingClassifier(max_iter=150, learning_rate=.1, max_leaf_nodes=31, early_stopping=False, random_state=0).fit(X[s == 0], y[s == 0])
        p = np.clip(m.predict_proba(X)[:, 1], 1e-6, 1-1e-6); sc = np.log(p/(1-p)); thr = np.quantile(sc[(s == 1) & (y == 0)], .99)
        for h in HID: res[nm][h].append((sc[(s == 2) & (w.defect_id.values == h)] <= thr).mean() * 100)
        res[nm]["ALL"].append((sc[(s == 2) & (y == 1)] <= thr).mean() * 100)
print("miss rate %% at 1%% FR (mean of 6 splits)   base   +engineered")
for h in HID + ["ALL"]: print("  %-8s %6.1f %6.1f" % (h, np.mean(res["base"][h]), np.mean(res["eng"][h])))
