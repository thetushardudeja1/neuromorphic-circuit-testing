# Provenance of every modelling choice (novelty 5: dataset as a documented resource)

| Element | Value / method | Source |
|---|---|---|
| Neuron topology | 21 transistors + Cm + output resistor; comparator, positive feedback, reset, Rqst/Ack handshake | El-Sayed et al., IOLTS 2020 Fig. 1 = Serrano-Gotarredona, TCAS-I 2006 Fig. 10 (Positive Event Block) |
| Defect: transistor stuck-on | 10 ohm drain-source short, one device at a time | El-Sayed 2020 |
| Defect: transistor open gate | gate cut from its net and driven by V(g,s) = 0.5 V(d,s) | Esen et al. 2016 |
| Defect: Cm, output resistor | +-50 % | El-Sayed 2020 |
| 46 defect list | 21 stuck-on + 21 open-gate + Cm +-50 % + Rout +-50 % | derived from the above |
| Stimulus | 10 us current pulse, 50/100/200/400 nA, starts at 5 us | El-Sayed 2020 Fig. 2a (0.1-0.2 uA range) extended to 4 amplitudes |
| Process (TSMC 65 nm, 3.3 V devices) | foundry model library on the VIT server; global draws N(0,1/3) on random1..10 and random1_mim exactly as the model card's AGAUSS(0,1,3) | model card itself (not published) |
| Local mismatch | the model card's own mismatch block (Pelgrom-type, `sigma` = 1); run 1 of every Monte Carlo set is HSPICE's nominal sample, runs 2..K are independent draws; one seed per deck, logged | model card + `.option seed` in manifest.json |
| Corners | MC (62 %), TT, SS, FF (12.5 % each) | design choice, logged per deck |
| Threshold-shift knob | BSIM4 `_delvto` instance parameter of the foundry sub-circuit | model card (verified: +50 mV on mn1 changes the readouts) |
| Readout tap | 1 kohm in series with 0-100 fF on Vm | design choice (multiplexer on-resistance + ADC input capacitance); effect measured in the `tap` group |
| Supply-current readouts | integral of I(Vdd) over 5-25 us and 5-15 us, peak supply current | derived: supply current exposed the 4 defects hidden to spikes + Vm readouts in the GF180 set |
| Internal-node readouts | tail, n3, mid, n4 at the Rqst-rise instant, plus extrema | diagnostic-mode upper bound (needs on-chip taps) |
| Sensitivity group (novelty 1) | nominal TT, one parameter nudged at a time: 21 device Vth +-10 mV, Cm +-2 %, Ibias +-5 %, Vref +-10 mV, Vrst +-10 mV | finite differences; null space = unidentifiable directions |
| Drift group (novelty 2) | matched sweeps: mn1 Vth +-2..40 mV, Cm +-1..20 %; converted to sigma units with the measured healthy spread | measured, not assumed |
| Tap group (novelty 4) | 0/10/25/50/100 fF on healthy neurons; all 46 defects at 0 and 25 fF, matched | measured |
| Behavioural fault model (novelty 3) | derived afterwards from the data: per defect, the shift of each feature relative to the matched nominal run | analysis step, no assumption |
| Not claimed | published detection rates, a "ghost spike" class (not observed), lot-to-lot spread | see literature survey |
