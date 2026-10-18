import warnings, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")
df = pd.read_csv("data/gf180/supplement_supply_current_readouts.csv.gz"); df["lat"] = df.t1 - 5e-6; df["per"] = df.t2 - df.t1; df["width"] = df.tf1 - df.t1
SPIKE = ["lat", "per", "width", "tl_avg", "tl_max", "t6"]; ANALOG = ["vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip"]
SUP = ["qdd_all", "qdd_sp", "ipk"]; NODE = ["tail_t", "n3_t", "mid_t", "n4_t", "n3min", "midpk", "tailmax", "tailmin", "n4pk"]
allf = SPIKE + ANALOG + SUP + NODE
w = df.pivot_table(index=["task", "die", "defect_id"], columns="stim_nA", values=allf, aggfunc="first")
w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]; w = w.reset_index()
def cols(fs): return [c for c in w.columns if "@" in c and c.split("@")[0] in fs]
sets = {"spike": cols(SPIKE), "spike+analog (current)": cols(SPIKE + ANALOG), "+supply current": cols(SPIKE + ANALOG + SUP),
        "+node voltages": cols(SPIKE + ANALOG + NODE), "+supply+nodes": cols(allf), "supply only": cols(SUP), "nodes only": cols(NODE)}
HID = ["mna_on", "mn2_off", "mna_off", "mn3_off"]
def oof(X, y, g):
    s = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, g):
        m = HistGradientBoostingClassifier(max_iter=100, learning_rate=.1, max_leaf_nodes=15, early_stopping=False, random_state=0).fit(X[tr], y[tr])
        p = np.clip(m.predict_proba(X[te])[:, 1], 1e-6, 1 - 1e-6); s[te] = np.log(p / (1 - p))
    return s
print("healthy %d ; per defect %s" % ((w.defect_id == "healthy").sum(), w[w.defect_id != "healthy"].defect_id.value_counts().to_dict()))
print("miss rate %% at 1%% false reject (out-of-fold, grouped by die), healthy vs ONE hidden defect at a time")
print("%-24s" % "feature set" + "".join("%9s" % h for h in HID) + "    all4")
for nm, c in sets.items():
    row = []
    for h in HID + ["ALL"]:
        keep = (w.defect_id == "healthy") | ((w.defect_id == h) if h != "ALL" else w.defect_id.isin(HID))
        sub = w[keep]; y = (sub.defect_id != "healthy").astype(int).values; X = sub[c].to_numpy(float)
        sc = oof(X, y, sub["die"].values); thr = np.quantile(sc[y == 0], .99)
        row.append((sc[y == 1] <= thr).mean() * 100)
    print("%-24s" % nm + "".join("%9.1f" % r for r in row))

print("\nSupply readout with measurement noise (relative Gaussian on each supply value, added after simulation); spike+analog+supply")
rng = np.random.default_rng(1)
cs = sets["spike+analog (current)"]; cu = sets["supply only"]
for rel in [0, 0.005, 0.02, 0.05, 0.10]:
    row = []
    for h in HID + ["ALL"]:
        keep = (w.defect_id == "healthy") | ((w.defect_id == h) if h != "ALL" else w.defect_id.isin(HID))
        sub = w[keep]; y = (sub.defect_id != "healthy").astype(int).values
        Xs = sub[cs].to_numpy(float); Xu = sub[cu].to_numpy(float); Xu = Xu * (1 + rel * rng.standard_normal(Xu.shape))
        sc = oof(np.hstack([Xs, Xu]), y, sub["die"].values); thr = np.quantile(sc[y == 0], .99)
        row.append((sc[y == 1] <= thr).mean() * 100)
    print("noise %4.1f %%        " % (rel * 100) + "".join("%9.1f" % r for r in row))
