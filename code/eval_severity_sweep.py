"""Severity sweep (GF180, 100 nA): how detectable are graded defects? Stuck-on resistance R (10 ohm..1 Mohm) and open-gate blend b (1.0 full .. 0.1 weak).
Detector trained on healthy vs ALL severities (mix) and, separately, on healthy vs the catastrophic extremes only (R=10, b=1) to see if a detector trained
on gross defects catches mild ones. Die-based splits (5), 1 % false reject, readout families: spike / +Vm / +supply / +nodes."""
import warnings
import numpy as np, pandas as pd
import dataset_loader as cw
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
d = pd.read_csv("data/gf180/severity_sweep_readouts.csv.gz", low_memory=False); d = d[d.status.isin(["ok", "ok_relaxed"])] if "status" in d.columns else d
d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1
d["sev"] = np.where(d.defect_id == "healthy", "healthy", d.variant.fillna(""))
FAM = {"spike only": cw.SPIKE, "spike+Vm": cw.SPIKE + cw.ANALOG, "spike+Vm+supply": cw.SPIKE + cw.ANALOG + cw.SUP, "+nodes": cw.SPIKE + cw.ANALOG + cw.SUP + cw.NODE}
dev = d.defect_id.str.rsplit("_", n=1).str[0].where(d.defect_id != "healthy", "healthy")
y = (d.defect_id != "healthy").astype(int).values; sev = d.sev.values; dies = np.array(sorted(d["die"].unique()))
print("neurons %d (healthy %d), dies %d" % (len(d), (y == 0).sum(), len(dies)))
SEV_ON = ["R=10", "R=100", "R=1000", "R=10000", "R=100000", "R=1e+06"]; SEV_OFF = ["b=1", "b=0.5", "b=0.25", "b=0.1"]
def run(train_mask_fn, fs):
    X = d[[c + "" for c in [f for f in fs if f in d.columns]]].to_numpy(float); res = {s: [] for s in SEV_ON + SEV_OFF}; dev_res = {}
    for sd in range(5):
        dd = dies.copy(); np.random.default_rng(100 + sd).shuffle(dd); a, b = int(.6 * len(dd)), int(.8 * len(dd))
        s = d["die"].map({**{x: 0 for x in dd[:a]}, **{x: 1 for x in dd[a:b]}, **{x: 2 for x in dd[b:]}}).values
        tr = (s == 0) & train_mask_fn(); va, te = s == 1, s == 2
        m = HistGradientBoostingClassifier(max_iter=100, learning_rate=.1, max_leaf_nodes=15, early_stopping=False, random_state=0).fit(X[tr], y[tr])
        p = np.clip(m.predict_proba(X)[:, 1], 1e-6, 1 - 1e-6); sc = np.log(p / (1 - p)); thr = np.quantile(sc[va & (y == 0)], .99)
        for k in res: res[k].append((sc[te & (sev == k)] <= thr).mean() * 100)
    return {k: np.mean(v) for k, v in res.items()}
def show(title, train_fn):
    print("\n=== %s ===\n  missed %% at 1%% false reject, pooled over the 21 devices" % title)
    print("  %-17s" % "readouts" + "".join("%9s" % k for k in SEV_ON) + " |" + "".join("%7s" % k for k in SEV_OFF))
    for nm, fs in FAM.items():
        r = run(train_fn, fs); print("  %-17s" % nm + "".join("%9.1f" % r[k] for k in SEV_ON) + " |" + "".join("%7.1f" % r[k] for k in SEV_OFF), flush=True)
show("detector trained on healthy vs ALL severities", lambda: np.ones(len(d), bool))
show("detector trained on healthy vs CATASTROPHIC only (R=10, b=1)", lambda: (y == 0) | np.isin(sev, ["R=10", "b=1"]))

# ---- per-device detail (detector trained on healthy vs all severities; mean of 5 die splits)
dev = d.defect_id.str.rsplit("_", n=1).str[0].where(d.defect_id != "healthy", "healthy").values
def per_device(fs):
    X = d[[f for f in fs if f in d.columns]].to_numpy(float); acc = {}
    for sd in range(5):
        dd = dies.copy(); np.random.default_rng(100 + sd).shuffle(dd); a, b = int(.6 * len(dd)), int(.8 * len(dd))
        s = d["die"].map({**{x: 0 for x in dd[:a]}, **{x: 1 for x in dd[a:b]}, **{x: 2 for x in dd[b:]}}).values
        m = HistGradientBoostingClassifier(max_iter=100, learning_rate=.1, max_leaf_nodes=15, early_stopping=False, random_state=0).fit(X[s == 0], y[s == 0])
        p = np.clip(m.predict_proba(X)[:, 1], 1e-6, 1 - 1e-6); sc = np.log(p / (1 - p)); thr = np.quantile(sc[(s == 1) & (y == 0)], .99)
        for dv in sorted(set(dev) - {"healthy"}):
            for sv in SEV_ON + SEV_OFF:
                mk = (s == 2) & (dev == dv) & (sev == sv)
                if mk.sum(): acc.setdefault((dv, sv), []).append((sc[mk] <= thr).mean() * 100)
    return pd.Series({k: np.mean(v) for k, v in acc.items()}).unstack()[SEV_ON + SEV_OFF]
for nm, fs in [("spike+Vm", FAM["spike+Vm"]), ("spike+Vm+supply", FAM["spike+Vm+supply"])]:
    T = per_device(fs); T.to_csv("results/gf180_severity_per_device_%s.csv" % nm.replace("+", "_"))
    print("\n=== per-device miss %% (%s), devices that are NOT reliably caught (miss > 20%%) already at stuck-on R=1000 ohm or at open-gate b=0.5 ===" % nm)
    bad = T[(T["R=1000"] > 20) | (T["b=0.5"] > 20)]
    print((bad.round(0)).to_string() if len(bad) else "  none")
    print("  devices caught (miss <= 20%%) at R=100000: %d of 21 | at b=0.25: %d of 21" % ((T["R=100000"] <= 20).sum(), (T["b=0.25"] <= 20).sum()))
