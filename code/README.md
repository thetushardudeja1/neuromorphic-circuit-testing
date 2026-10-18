# Code index

These are the scripts that produced the data and the results, with paths adjusted to this folder layout. Run them from the release root, for example `python code/eval_detection_by_readout.py`.
Requirements: Python 3, pandas, numpy, scikit-learn 1.6. The TSMC 65 nm data is not in this repository, so only the GF180 flow and the `gf180_*` evaluations run as-is. The generators additionally need ngspice 41 and the GF180MCU PDK (GF180) or HSPICE and the foundry model library (TSMC 65 nm); those are not included.

## Data loading
| File | Purpose |
|---|---|
| `dataset_loader.py` | loads either technology as one row per neuron with columns `<readout>@<stimulus nA>`; die-based splits; the 1 % false-reject metric |
| `tsmc65_parse_measurements.py` | converts the raw HSPICE measurement files (`raw_hspice_measurements.tgz`, extracted to `data/tsmc65/raw/`) into a readouts table |

## Data generation
| File | Purpose |
|---|---|
| `circuit_definition.py` | the 21 devices, the 46 defects and the design values (shared by both flows) |
| `gf180_generator.py` | GF180 / ngspice generator: netlist, die-level and local variation, defects, parallel runs, extension groups |
| `gf180_supply_supplement_generator.py` | re-simulates matched GF180 neurons with supply-current and internal-node readouts |
| `gf180_severity_sweep_generator.py` | graded defect severity (stuck-on resistance, partially open gates) |
| TSMC 65 nm deck generators and batch runner | not included in the public repository (licensed foundry model library) |

## Evaluation (one script per result section in docs/RESULTS.md)
| File | Result section |
|---|---|
| `eval_detection_by_readout.py` | A: detection by readout set |
| `eval_supply_noise_tolerance.py` | B: noise tolerance of the supply readout |
| `eval_readout_design_study.py` | B (normalised ratios), C (minimal test), E (stimulus choice) |
| `eval_defect_location.py`, `eval_fault_model_and_groups.py` | D: defect location, behaviour classes, look-alike groups |
| `eval_identifiability.py` | E: identifiability |
| `eval_drift_detectability.py` | F: parametric drift |
| `eval_tap_loading.py` | G: readout-tap loading |
| `eval_cascade_and_calibration.py` | H: cascade; I: corner calibration |
| `eval_cross_technology_transfer.py` | J: cross-technology transfer |
| `eval_severity_sweep.py` | K: graded severity |
| `gf180_eval_*.py` | the GF180 analyses (referencing and selective readout, ablation, supply supplement, engineered features) |
