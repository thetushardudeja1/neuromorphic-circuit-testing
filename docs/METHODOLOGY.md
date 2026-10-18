# Methodology

## 1. Circuit
Integrate-and-fire neuron of El-Sayed et al. (IOLTS 2020, Fig. 1), equal to the positive-event block of Serrano-Gotarredona et al. (TCAS-I 2006, Fig. 10): membrane capacitor Cm,
a comparator against a reference, positive feedback, a reset switch, an inverter and Rqst/Ack handshake stage, and an output stage. 21 transistors, one capacitor, one output
resistor. Connectivity and design values: `CIRCUIT.md`. Published values used: supply 3.3 V, Cm about 140 fF, comparator reference 0.5 V above the reset level, stimulus a 10 us
current pulse. Our own design choices (Vreset 1.1 V, Vref 1.6 V, bias 10 uA, device sizes, output load 20 kohm, Rqst arbiter, Ack delay) are listed in `PROVENANCE.md`.

## 2. Defect model (46 defects, El-Sayed 2020)
| Defect | Model |
|---|---|
| transistor stuck-on (21) | 10 ohm drain-source short |
| transistor stuck-off / open gate (21) | gate cut from its net and driven with V(g,s) = 0.5 V(d,s) (Esen et al., ITC 2016) |
| membrane capacitor (2) | Cm +50 % and -50 % |
| output resistor (2) | +50 % and -50 % |

One defect per neuron. Defect ids: `mp1_on`, `mp2_on`, `mn4_on`, `mc1_on`, `mc2_on`, `mn5_on`, `mn6_on`, `mnr_on`, `mn1_on`, `mn2_on`, `mn3_on`, `mi1_on`, `mi2_on`, `mp4_on`, `mna_on`, `mnb_on`, `mpr_on`, `mpa_on`, `mp5_on`, `mnc_on`, `mp3_on`, `mp1_off`, `mp2_off`, `mn4_off`, `mc1_off`, `mc2_off`, `mn5_off`, `mn6_off`, `mnr_off`, `mn1_off`, `mn2_off`, `mn3_off`, `mi1_off`, `mi2_off`, `mp4_off`, `mna_off`, `mnb_off`, `mpr_off`, `mpa_off`, `mp5_off`, `mnc_off`, `mp3_off`, `cm_plus50`, `cm_minus50`, `rout_plus50`, `rout_minus50`.

## 3. Stimulus and timing
Input current pulse of 50, 100, 200 or 400 nA, starting at 5 us, width 10 us. Observation window 25 us (7 us for five defects that make the neuron fire continuously in GF180:
`mp1_on, mp1_off, mnb_on, mpr_on, mi1_off`). Each neuron is simulated at all four amplitudes with identical device parameters.

## 4. Process variation
**Die structure.** A die is a shared global process draw; the neurons of one die differ only by local mismatch. Corner cycle by die index: MC, MC, MC, MC, TT, SS, FF, MC
(5/8 Monte Carlo dies, 1/8 each of TT, SS, FF).
- **GF180 (ngspice):** global draws come from the PDK's own `statistical` and `mimcap_statistical` blocks (every `agauss(m,s,n)` replaced by one explicit draw per die, seeded by die index).
  Local mismatch is a per-transistor threshold-voltage shift drawn in Python with the PDK's Pelgrom form, sigma = 0.7071 * par_vth * 1e-6 / sqrt(Leff * Weff), and **logged per neuron** (`dvt` in the manifest).
  ngspice cannot replay its own random seeds, which is why the draws are made explicitly.
- **TSMC 65 nm (HSPICE):** global draws as in the model card (`random1..10`, `random1_mim`, N(0, 1/3), explicit per die); local mismatch from the card's own mismatch block through
  Monte Carlo (`sweep monte=9`), one seed per deck, logged in each deck's `manifest.json`. Run 1 of every Monte Carlo set is HSPICE's nominal sample (`is_nominal = 1`); runs 2-9 are independent draws.
  One deck is one class (one defect or one healthy replicate) of one die, measured at all four stimuli with the same draws; different classes have different seeds, so all neurons in the main set are independent.

## 5. Readouts (measured directly by the simulator; no noise is added in the data)
Spike timing from the output `vspike` (threshold 1.65 V): `t1,t2,t3,t6,t12` rising edges, `tf1` first falling edge, `tl_avg/min/max` output statistics in the last 2 us.
Membrane-voltage readouts: `vtrip` (Vm when the comparator output n1 falls through 3.0 V), `vpk` (maximum), `vidle` (Vm at 4.9 us), `vmin`, `vrst` (Vm right after the first spike).
Handshake timing: `tcmp` (Rqst rise to spike rise), `ttrip` (Vm crossing Vref to Rqst rise).
Supply current (added): `qdd_all` and `qdd_sp` (charge drawn from Vdd over 5-25 us and 5-15 us), `ipk` (peak supply current).
Internal nodes (added): `tail_t, n3_t, mid_t, n4_t` (node voltages at the Rqst rise), `n3min, midpk, tailmax, tailmin, n4pk` (extrema).
Full definitions and units: `DATA_DICTIONARY.md`.

## 6. Extension experiments
- **Sensitivity (identifiability):** nominal TT neuron; one parameter nudged at a time (each device's threshold voltage +-10 mV, Cm +-2 %, bias current +-5 %, Vref +-10 mV, Vrst +-10 mV).
- **Drift:** matched neurons; `mn1` threshold voltage +-2..40 mV and Cm +-1..20 % (TSMC); +-0.5..20 sigma of the PDK spread (GF180).
- **Tap loading:** a readout tap (1 kohm in series with 10 / 25 / 50 / 100 fF on the membrane node); healthy neurons at all levels and all 46 defects at 0 and 25 fF, matched to the untapped neuron.

## 7. Provenance and reproducibility
Every modelling choice and its source: `PROVENANCE.md`. The generators in `code/` produce the data exactly as run (`gf180_generator.py` for GF180; `tsmc65_deck_generator.py` and `tsmc65_batch_runner.py` for TSMC).
GF180: the parameters of every neuron are in `neuron_parameters.jsonl.gz`. TSMC: seeds and the full condition list of every deck are in the manifests inside `raw_hspice_measurements.tgz`.
