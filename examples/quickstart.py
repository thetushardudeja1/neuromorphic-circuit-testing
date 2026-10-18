"""Reproduce the GF180 headline result from the released files: faulty neurons missed at 1 % false
reject, spike train only versus spike train + membrane readouts.
Run from the repository root:  python examples/quickstart.py   (needs pandas, numpy, scikit-learn)"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
from dataset_loader import gf180, cols, split, hgb, logit, miss_at_1pct, SPIKE, ANALOG

w = gf180()
y = (w.defect_id != "healthy").astype(int).values
print("neurons %d (healthy %d), dies %d" % (len(w), (y == 0).sum(), w["die"].nunique()))
for name, fams in [("spike train only", SPIKE), ("+ membrane readouts", SPIKE + ANALOG)]:
    X = w[cols(w, fams)].to_numpy(float); miss = []
    for seed in range(3):
        tr, va, te = split(w, seed)
        s = logit(hgb().fit(X[tr], y[tr]).predict_proba(X)[:, 1])
        miss.append(miss_at_1pct(s, y, va, te)[0])
    print("%-22s faulty neurons missed: %5.1f %%  (mean of 3 die splits)" % (name, np.mean(miss)))
