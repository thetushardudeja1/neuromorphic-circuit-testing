# Results

All results: split by die, detector threshold at 1 % false reject of healthy validation neurons, miss rate on test dies. Scripts are in `code/`, raw outputs in `results/`.
Numbers are means over the stated number of random die splits (+- sd where given). All results are simulation-only.

## A. Detection by readout set (TSMC 65 nm, 60,000 neurons, 6 die splits)
| Readouts | Faulty neurons missed |
|---|---|
| spike train only | 11.4 % +- 2.8 |
| + membrane-voltage readouts | 3.3 % +- 1.3 |
| + supply current | 0.0 % +- 0.0 |
| + supply current + internal nodes | 0.1 % +- 0.2 |
| supply current only | 4.5 % +- 0.9 |

Defects missed by more than 5 % (spike / + Vm / + Vm and supply): `mna_on` 81 / 62 / 0.2, `mna_off` 81 / 48 / 0.0, `mnb_off` 85 / 27 / 0.0, `mn2_off` 79 / 3.9 / 0.0, `mn3_off` 82 / 1.3 / 0.0 (%).
GF180 (49,840 neurons, 6 die splits): spike train 10.3 % +- 0.8 missed, + analog readouts 3.7 % +- 0.5; the same devices are hidden. GF180 supplementary run (2,080 neurons, 120 per defect, grouped by die, each defect against healthy):

| Defect | spike | + Vm | + Vm and supply | + nodes |
|---|---|---|---|---|
| `mna_on` | 89.2 | 67.5 | 18.3 | 0.0 |
| `mn2_off` | 85.8 | 56.7 | 2.5 | 0.0 |
| `mna_off` | 65.8 | 23.3 | 2.5 | 0.0 |
| `mn3_off` | 93.3 | 24.2 | 0.8 | 0.0 |

## B. Noise tolerance of the supply readout (TSMC, relative Gaussian noise on every supply value)
| Noise | 0 % | 0.5 % | 1 % | 2 % | 5 % | 10 % |
|---|---|---|---|---|---|---|
| Faulty missed | 0.0 | 0.0 | 0.0 | 0.0 | 0.3 | 0.9 |

Defects still missed >5 %: `mna_on` (12 % at 5 % noise; 31 % at 10 %), `mna_off` (11 % at 10 %). Self-normalised supply ratios (charge per spike, cross-stimulus ratios) gave no benefit: 0.4 vs 0.3 % at 5 %, 1.2 vs 1.1 % at 10 %, 2.1 vs 2.1 % at 20 % noise.

## C. Minimal test (TSMC): stimulus subsets (missed %, spike + Vm + supply readouts)
| Stimuli (nA) | 50 | 100 | 200 | 400 | any two | all four |
|---|---|---|---|---|---|---|
| Missed | 0.5 | 0.1 | 0.3 | 0.4 | 0.0-0.1 | 0.0 |

With spike + Vm only, all four stimuli miss 2.8 %; with spikes only, 14.0 %. A reduced four-feature set (latency, period, charge, peak current) misses 5.7 % - not sufficient. One pulse with all readouts is enough for pass/fail.

## D. Defect location, 46 classes (TSMC, faulty test neurons)
| Readouts | top-1 | top-3 |
|---|---|---|
| spike | 72.6 % | 90.5 % |
| + Vm | 91.3 % | 100 % |
| + Vm and supply | 96.2 % | 100 % |

Only `mn1_on` and `mn3_on` form a look-alike group. Behaviour classes (rules on measured quantities, `results/tsmc65_behavioural_fault_model.csv`): 14 defects with no spike-level effect, 11 parametric timing, 9 dead, 1 stuck-at-X, 5 stuck-at-1, 3 saturated, 3 long spike.

## E. Identifiability (sensitivity group, TSMC; see KNOWN_ISSUES item 4)
Finite-difference sensitivity of the readouts to 25 parameters, in units of the healthy population spread (0.1 % instrument floor, signatures clipped at 50 sigma). No exactly unidentifiable direction and no pair of parameters with look-alike signatures. Directions resolvable above 1 sigma per nudge (four stimuli): spike + Vm 19 of 25, + supply 23 of 25, + internal nodes 25 of 25. By stimulus subset (spike + Vm + supply): one stimulus 8-9, two stimuli 12-14, four stimuli 20 of 25 - more stimuli help identify parameters even though one suffices to detect. The weakest directions are combinations of `mn2, mna, mnc, mpa, mnb, mnr`, the devices that hide from spikes.

## F. Parametric drift (TSMC, 3 sigma detection)
| | spike + Vm | + supply | per-neuron before/after |
|---|---|---|---|
| `mn1` threshold drift | 89 mV | 13 mV | 1.8 mV |
| Cm drift | 12 % | 12 % | 0.17 % |

Population-referenced values use the spread of healthy neurons; before/after compares a neuron with its own earlier measurement (upper bound, KNOWN_ISSUES item 14).

## G. Readout-tap loading (TSMC, 10 dies)
A 25 fF tap shifts the strongest readout by 5.6 population sigma. A detector trained without a tap rejects 1.2 / 17.5 / 73.8 / 100 / 100 % of good neurons at 0 / 10 / 25 / 50 / 100 fF. Retrained with tapped examples (5 dies, tested on 5 others): 2.5 % false reject at 25 fF with 0.6 % defects missed; 50 and 100 fF are not fully recovered (60 and 35 % false reject; few examples).

## H. Cost-ordered cascade (TSMC, 10 % faulty mix, 1 % overall false reject)
| Neurons sent to the supply + Vm stage | 1.6 % | 4.1 % | 11.0 % | 19.8 % | 43.9 % | 100 % |
|---|---|---|---|---|---|---|
| Faulty missed | 12.1 % | 8.2 % | 4.8 % | 2.9 % | 0.7 % | 0.0 % |

## I. False-reject calibration across corners (TSMC)
One global threshold from pooled validation dies gives false reject 0.70 % in Monte Carlo dies and 0.00 % in TT, SS and FF dies (those dies have no random global variation); per-corner thresholds change nothing material. Spread of false reject between dies: sd 2.3 points; 2.2 % of dies exceed 3 %.

## J. Cross-technology transfer (spike + Vm readouts, 40 features)
| Train -> test | threshold from source: FR / miss | recalibrated on target healthy: FR / miss | in-technology |
|---|---|---|---|
| GF180 -> TSMC, raw | 100 % / 0 % | 0.6 % / 72.9 % | 1.0 % / 5.4 % |
| GF180 -> TSMC, per-technology standardised | 67.3 % / 2.0 % | 0.2 % / 38.7 % | |
| TSMC -> GF180, raw | 100 % / 0 % | 0.0 % / 100 % | 1.1 % / 3.8 % |
| TSMC -> GF180, per-technology standardised | 18.8 % / 14.8 % | 1.6 % / 34.2 % | |

Trained detectors do not transfer; the method (which defects hide, which readout exposes them) does: the same devices are hidden in both technologies.

## K. Graded severity sweep (GF180, 100 nA only; supplementary)
Stuck-on short resistance from 10 ohm to 1 Mohm and partially open gates (blend b from 1.0 = fully open to 0.1), 21 devices, 40 dies, one neuron per device and severity per die (10,000 neurons including 1,600 healthy). The severity levels are our own extension of the catastrophic model. Detector trained on healthy versus all severities; faulty neurons missed (%) at 1 % false reject, pooled over the 21 devices:

| Readouts | R=10 | 100 | 1k | 10k | 100k | 1M | b=1 | 0.5 | 0.25 | 0.1 |
|---|---|---|---|---|---|---|---|---|---|---|
| spike | 13.5 | 13.6 | 16.2 | 36.5 | 50.4 | 69.9 | 21.7 | 50.0 | 63.9 | 81.1 |
| + Vm | 9.2 | 10.5 | 9.8 | 24.9 | 47.5 | 66.7 | 17.7 | 41.9 | 57.7 | 76.5 |
| + Vm and supply | 8.0 | 9.0 | 9.2 | 13.2 | 27.9 | 66.3 | 13.1 | 40.8 | 53.5 | 69.4 |
| + internal nodes | 1.2 | 1.0 | 3.6 | 7.1 | 18.0 | 63.6 | 2.6 | 22.6 | 43.5 | 67.4 |

- Stuck-on shorts up to 1 kohm are as detectable as the 10 ohm short; from 10 kohm upwards the miss rate climbs, and supply current helps most there (10 kohm: 24.9 -> 13.2 %; 100 kohm: 47.5 -> 27.9 %). A 1 Mohm short is practically invisible to every readout set, as expected for an electrically negligible defect.
- Open gates are harder: a half-open gate (b = 0.5) is missed 41-50 % of the time with spike, Vm and supply readouts, and 22.6 % with internal nodes.
- A detector trained on the catastrophic extremes only (R = 10 ohm, b = 1) catches mild defects worse than one trained on the severity mix (see `results/gf180_severity_sweep.txt`).
- Devices `mna` and `mpa` (stuck-on) stay mostly missed in this sweep even with supply current (78-98 %), whereas the TSMC single-stimulus result misses 0.1 %. The sweep has few training examples per device (24 training dies, one stimulus), so do not generalise this; per-device tables: `results/gf180_severity_per_device_*.csv`. Each per-device cell rests on about 40 test neurons.
