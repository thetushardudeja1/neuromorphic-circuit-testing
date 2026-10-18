"""circuit-derived behavioural fault model (TSMC 65 nm main data, 100 nA stimulus for the rules; all stimuli for the classifier).
(A) per defect: behaviour class by explicit rules on measured quantities (El-Sayed taxonomy: dead, saturated/free-running, stuck-at-1, stuck-at-X, long spike,
    parametric timing, no effect), with the measured fractions behind each label.  (B) which defects the readouts cannot tell apart: 46-class
    classifier (spike+Vm+supply) on test dies; defects confused with each other in >25 % of cases are merged into an equivalence group."""
import numpy as np, pandas as pd, warnings
from sklearn.ensemble import HistGradientBoostingClassifier
warnings.filterwarnings("ignore")
d = pd.read_csv("data/tsmc65/readouts.csv.gz", low_memory=False); d = d[(d.kind == "main") & (d.is_nominal == 0)].copy()
d["lat"] = d.t1 - 5e-6; d["per"] = d.t2 - d.t1; d["width"] = d.tf1 - d.t1; d["neuron"] = d.deck + "_r" + d.mc_run.astype(str)
a = d[d.stim_nA == 100]; hl = a[a.defect_id == "healthy"]
H = dict(lat=hl.lat.median(), per=hl.per.median(), width=hl.width.median(), slat=hl.lat.std(), tl=hl.tl_avg.median())
print("healthy @100 nA: latency %.3g s, period %.3g s, width %.3g s, late-window mean level %.3g V (sd latency %.2g s)" % (H["lat"], H["per"], H["width"], H["tl"], H["slat"]))
rows = []
for k, g in a.groupby("defect_id"):
    if k == "healthy": continue
    spk = g.t1.notna().mean(); gs = g[g.t1.notna()]
    r = dict(defect=k, n=len(g), spike_frac=spk,
             lat_ratio=gs.lat.median() / H["lat"] if len(gs) else np.nan, lat_shift_sigma=(gs.lat.median() - H["lat"]) / H["slat"] if len(gs) else np.nan,
             period_ratio=gs.per.median() / H["per"] if gs.per.notna().any() else np.nan, width_ratio=gs.width.median() / H["width"] if len(gs) else np.nan,
             late_level=g.tl_avg.median())
    if spk < 0.1:
        lvl = g.tl_avg.median()            # output level with no spikes: low = dead, high = stuck-at-1, in between = stuck-at-X (floating)
        c = "stuck-at-1 (output high, no spikes)" if lvl > 2.5 else ("dead (no spikes)" if lvl < 0.3 else "stuck-at-X (output at %.2f V, no spikes)" % lvl)
    elif r["width_ratio"] > 3: c = "long spike"
    elif r["period_ratio"] < 0.5: c = "saturated / free-running"
    elif abs(r["lat_shift_sigma"]) > 3 or abs(np.log(r["period_ratio"])) > 0.05 or abs(np.log(r["width_ratio"])) > 0.2: c = "parametric timing"
    else: c = "no spike-level effect (timing within 3 sigma)"
    if spk >= 0.1 and spk < 0.9: c += " + mixed (%.0f%% of neurons spike)" % (spk * 100)
    r["class"] = c; rows.append(r)
FM = pd.DataFrame(rows).set_index("defect")
print("\n(A) behaviour classes (counts):"); print(FM["class"].str.replace(r" \+ mixed.*", "", regex=True).value_counts().to_string())
# (B) equivalence groups
F = ["lat", "per", "width", "tl_avg", "tl_max", "t6", "vtrip", "vpk", "vidle", "vmin", "vrst", "tcmp", "ttrip", "qdd_all", "qdd_sp", "ipk"]
w = d.pivot_table(index=["neuron", "die", "defect_id"], columns="stim_nA", values=F, aggfunc="first"); w.columns = ["%s@%d" % (f, int(s)) for f, s in w.columns]; w = w.reset_index()
cols = [c for c in w.columns if "@" in c]
dies = np.array(sorted(w["die"].unique())); np.random.default_rng(1).shuffle(dies); tr_d = set(dies[:100]); trm = w["die"].isin(tr_d).values
fa = w[w.defect_id != "healthy"]; mtr = (fa["die"].isin(tr_d)).values
m = HistGradientBoostingClassifier(max_iter=200, learning_rate=.08, max_leaf_nodes=31, early_stopping=False, random_state=0).fit(fa.loc[mtr, cols].to_numpy(float), fa.defect_id[mtr])
Xte = fa.loc[~mtr, cols].to_numpy(float); yte = fa.defect_id[~mtr].values; pred = m.classes_[m.predict_proba(Xte).argmax(1)]
print("\n(B) 46-class defect-location accuracy (test dies): %.1f %%" % ((pred == yte).mean() * 100))
cl = list(m.classes_); C = pd.DataFrame(0.0, index=cl, columns=cl)
for t, p in zip(yte, pred): C.loc[t, p] += 1
C = C.div(C.sum(1), axis=0)
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
D = 1 - (C.values + C.values.T) / 2; np.fill_diagonal(D, 0)
lab = fcluster(linkage(squareform(D, checks=False), "complete"), 0.75, "distance")      # complete linkage: every pair in a group is confused >25 % of the time
G = [sorted(np.array(cl)[lab == k]) for k in sorted(set(lab))]; multi = [g for g in G if len(g) > 1]
print("   %d groups out of 46 defects (%d defects sit in a group with at least one look-alike)" % (len(G), sum(len(g) for g in multi)))
for g in sorted(multi, key=len, reverse=True)[:14]: print("   look-alike group:", ", ".join(g))
gid = {c: i for g, i in zip(G, range(len(G))) for c in g}; ge = np.mean([gid[t] == gid[p] for t, p in zip(yte, pred)]) * 100
print("   group-level accuracy: %.1f %%" % ge)
FM["group"] = [", ".join(g) for c in FM.index for g in G if c in g]
FM.round(4).to_csv("results/tsmc65_behavioural_fault_model.csv"); print("\nwrote results/tsmc65_behavioural_fault_model.csv")
