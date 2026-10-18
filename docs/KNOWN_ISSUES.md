# Known issues and limits - read before using the data

1. **Simulation only.** No silicon measurements. Measurement noise is not in the data; the noise-tolerance results add it afterwards.
2. **One circuit, two technologies.** Both datasets use the same topology; conclusions about other neuron designs are not supported.
3. **Models do not transfer between technologies as they are.** A detector trained on GF180 and applied to TSMC (and the reverse) rejects nearly all good neurons or misses most defects (RESULTS.md, section J). Train per technology.
4. **The TSMC sensitivity deck has only about 4 significant digits.** The `sens` rows come from a deck whose non-Monte-Carlo output was printed with 4 digits (about 0.1 % resolution). An 8-digit re-run exists on the lab server and is not part of this release, so identifiability results drawn from the 4-digit data are approximate. The Monte Carlo decks (main, drift, tap) print 7 digits and are not affected.
5. **GF180: 166 neurons were simulated with relaxed solver tolerances** (`ok_relaxed` in `solver_status.csv`). They are valid simulations but may differ slightly from default-tolerance results.
6. **GF180: five defects use a 7 us window** (`mp1_on, mp1_off, mnb_on, mpr_on, mi1_off`) because they fire continuously; `tl_*`, `t6` and `t12` are not comparable with the 25 us window.
7. **The TSMC main set is balanced by class, not by prevalence:** 1,200 neurons per defect and 4,800 healthy (4 replicate groups). Re-weight for a production-like fault mix when estimating overall rates.
8. **Internal-node readouts exist only for neurons that spike** (they are sampled at the Rqst rise); about 26 % of TSMC neurons never spike and have empty values there.
9. **The ghost-spike behaviour class of El-Sayed 2020 was not observed** in either technology.
10. **The defect model is the catastrophic one** (10 ohm shorts, fully open gates, +-50 % passives) taken from the literature. Graded severities exist only in the supplementary sweep (GF180, 100 nA), and its severity levels are our own extension.
11. **The drift and tap groups are small** (TSMC: 20 and 10 dies); per-condition statistics rest on 160 and 80 neurons.
12. **Instrument floor.** Where results are expressed in sigma units, a 0.1 % instrument resolution floor is assumed (stated wherever used).
13. **Population-median "neighbour referencing" did not improve detection** in these data; only per-neuron before/after comparison did (drift group).
14. **Per-neuron before/after drift limits are simulator-noise limited** (time-step interpolation jitter included), so they are upper bounds on what a real instrument could resolve.
