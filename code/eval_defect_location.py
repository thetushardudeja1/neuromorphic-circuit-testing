"""46-class defect LOCATION accuracy by readout set (TSMC 65 nm main, faulty neurons only, test dies, 4 stimuli)."""
import numpy as np, pandas as pd, warnings
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
d = pd.read_csv("data/tsmc65/readouts.csv.gz", low_memory=False); d = d[(d.kind == "main") & (d.is_nominal == 0) & (d.defect_id != "healthy")].copy()
d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1; d["neuron"] = d.deck + "_r" + d.mc_run.astype(str)
SP = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]; AN = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]; SU = ["qdd_all", "qdd_sp", "ipk"]
w = d.pivot_table(index=["neuron", "die", "defect_id"], columns="stim_nA", values=SP + AN + SU, aggfunc="first"); w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]; w = w.reset_index()
dies = np.array(sorted(w["die"].unique())); np.random.default_rng(1).shuffle(dies); tr = w["die"].isin(set(dies[:100])).values
for nm, fs in [("spike only", SP), ("spike + Vm", SP + AN), ("spike + Vm + supply", SP + AN + SU)]:
    cols = [c for c in w.columns if "@" in c and c.split("@")[0] in fs]
    m = HistGradientBoostingClassifier(max_iter=200, learning_rate=.08, max_leaf_nodes=31, early_stopping=False, random_state=0).fit(w.loc[tr, cols].to_numpy(float), w.defect_id[tr])
    P = m.predict_proba(w.loc[~tr, cols].to_numpy(float)); y = w.defect_id[~tr].values
    top3 = np.mean([y[i] in m.classes_[np.argsort(-P[i])[:3]] for i in range(len(y))])
    print("  %-22s top-1 %5.1f %%   top-3 %5.1f %%" % (nm, (m.classes_[P.argmax(1)] == y).mean() * 100, top3 * 100), flush=True)
