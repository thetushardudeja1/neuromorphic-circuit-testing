"""Cross-technology transfer. Study 6: cross-technology transfer (GF180 <-> TSMC 65 nm), same circuit, spike+Vm readouts only (supply current exists only in TSMC).
Train on one technology, test on the other: raw threshold from the source; threshold recalibrated on 20 % of the target's healthy dies; plus per-technology
standardisation (median/IQR of that technology's healthy neurons). Reference: model trained inside the target technology."""
import warnings
import numpy as np, pandas as pd
import dataset_loader as cw
warnings.filterwarnings("ignore")
G, T = cw.gf180(), cw.tsmc()
F = ["lat", "per", "width", "t6", "vtrip", "vpk", "vmin", "vrst", "tcmp", "ttrip"]
cols = [c for c in cw.cols(G, F) if c in T.columns]
def mat(w): return w[cols].to_numpy(float), (w.defect_id != "healthy").astype(int).values
def stdz(X, y):
    h = X[y == 0]; med = np.nanmedian(h, 0); iqr = np.nanpercentile(h, 75, 0) - np.nanpercentile(h, 25, 0); iqr[iqr == 0] = 1; return (X - med) / iqr
def evalset(src, tgt, name, seeds=(0, 1)):
    Xs, ys = mat(src); Xt, yt = mat(tgt); rows = []
    for sd in seeds:
        trs, vas, _ = cw.split(src, sd); _, vat, tet = cw.split(tgt, sd)      # target: val dies = calibration pool, test dies = evaluation
        res = {}
        for mode in ("raw", "per-tech standardised"):
            A, B = (Xs, Xt) if mode == "raw" else (stdz(Xs, ys), stdz(Xt, yt))
            m = cw.hgb().fit(A[trs], ys[trs]); ss = cw.logit(m.predict_proba(A)[:, 1]); st = cw.logit(m.predict_proba(B)[:, 1])
            thr_src = np.quantile(ss[vas & (ys == 0)], .99); thr_cal = np.quantile(st[vat & (yt == 0)], .99)
            res[mode] = ((st[tet & (yt == 0)] > thr_src).mean() * 100, (st[tet & (yt == 1)] <= thr_src).mean() * 100, (st[tet & (yt == 0)] > thr_cal).mean() * 100, (st[tet & (yt == 1)] <= thr_cal).mean() * 100)
        trt, vat2, tet2 = cw.split(tgt, sd); m = cw.hgb().fit(Xt[trt], yt[trt]); s = cw.logit(m.predict_proba(Xt)[:, 1]); th = np.quantile(s[vat2 & (yt == 0)], .99)
        res["in-technology"] = ((s[tet2 & (yt == 0)] > th).mean() * 100, (s[tet2 & (yt == 1)] <= th).mean() * 100, np.nan, np.nan); rows.append(res)
    print("\n=== %s ===\n  %-24s %s" % (name, "", "source threshold: FR / miss      | recalibrated on target healthy: FR / miss"))
    for k in ("raw", "per-tech standardised", "in-technology"):
        v = np.nanmean([r[k] for r in rows], 0); print("  %-24s %6.1f%% / %5.1f%%                  | %s" % (k, v[0], v[1], "  %6.1f%% / %5.1f%%" % (v[2], v[3]) if not np.isnan(v[2]) else "   (not applicable)"))
print("features used: %d (spike+Vm readouts at 4 stimuli, common to both)" % len(cols))
evalset(G, T, "train GF180 -> test TSMC"); evalset(T, G, "train TSMC -> test GF180")
