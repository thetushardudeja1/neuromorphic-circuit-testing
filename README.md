# IF-Neuron-Fault-Dataset v1.0

A transistor-level fault dataset for an analog **integrate-and-fire spiking neuron** (21 transistors; El-Sayed et al. IOLTS 2020 / Serrano-Gotarredona et al. TCAS-I 2006),
simulated in **two technologies** (open GF180MCU with ngspice; TSMC 65 nm with HSPICE) with **46 literature-based defects**, independent local mismatch, die-level process
variation, and readouts that go beyond the spike train: membrane voltages, **supply current** and internal nodes. It also contains controlled sensitivity, drift and
readout-tap-loading experiments. Every random draw is seeded and logged, so every neuron can be regenerated.

> **What this repository contains:** the full **GF180MCU** dataset (open PDK), all code for the GF180 flow, every
> evaluation script, and the result summaries for both technologies. The **TSMC 65 nm** simulated data and the TSMC
> deck generators are **not included**: they derive from a foundry model library licensed to the institute.
> TSMC numbers quoted below are aggregate analysis results.

## At a glance
| | GF180MCU (ngspice 41) | TSMC 65 nm (HSPICE V-2023.12-SP2) |
|---|---|---|
| Independent neurons in the main set | **49,840** (280 dies; per die 40 healthy + 3 per defect) | **60,000** (150 dies x 50 classes x 8 local-mismatch draws) |
| Stimulus | 10 us current pulse at 50 / 100 / 200 / 400 nA (all 4 on every neuron) | same |
| Defect classes | 46 defects + healthy | 46 defects + healthy (healthy in 4 replicate groups) |
| Corners | MC (global + local), TT, SS, FF | MC (global + local), TT, SS, FF |
| Readouts | 16 (spike timing, membrane voltages) | 28 (adds supply current and internal nodes) |
| Extension groups | sensitivity (51), drift (1,280), tap loading (1,320) neuron-conditions | sensitivity (1 deck), drift (20 dies), tap loading (10 dies) |
| Redistribution | derived from an open PDK, see below | **internal: derived from a licensed foundry model, do not redistribute** |

Supplementary: `data/gf180/supplement_*` re-simulates 2,080 of the same GF180 neurons (healthy plus the 4 hardest defects) with supply-current and internal-node readouts.
Supplementary: `data/gf180/severity_sweep_*` holds graded-severity defects (stuck-on resistance 10 ohm to 1 Mohm, partially open gates) at 100 nA with all readouts.

## Folder layout
```
IF-Neuron-Fault-Dataset_v1.0/
  README.md                     this file
  docs/
    METHODOLOGY.md              circuit, defect model, variation model, simulation set-up
    CIRCUIT.md                  netlist connectivity, design values, role of every device
    DATA_DICTIONARY.md          every column, unit and code list
    PROVENANCE.md               where every modelling choice comes from
    RESULTS.md                  what the dataset shows (headline numbers and experiment tables)
    KNOWN_ISSUES.md             caveats, flagged records, limits - read before using
    REFERENCES.md               literature and tools
  data/
    gf180/                      readouts.csv.gz, neuron_parameters.jsonl.gz, solver_status.csv, supplement_*
    (tsmc65/ not included: licensed foundry-model data)
    gf180_severity_sweep/       graded defect severity (supplementary)
  results/                      raw text/CSV output of every analysis script
  code/                         generators, parsers and evaluation scripts (see code/README.md)
  examples/quickstart.py        load the data and reproduce the headline result in a few minutes
  SHA256SUMS.txt                checksums of every data file
```

## Quick start
```python
import pandas as pd
g = pd.read_csv("data/gf180/readouts.csv.gz", low_memory=False)     # one row per neuron per stimulus
main = g[g.kind == "main"]
print(main.defect_id.value_counts().head())
```
`python examples/quickstart.py` pivots the GF180 data to one row per neuron and reproduces the GF180 headline (spike train only
versus + membrane readouts). It averages 3 die splits and gives about 10.9 % / 3.9 % missed (6-split values: 10.3 % / 3.7 %).
Scripts named `eval_*` without a `gf180_` prefix analyse the TSMC 65 nm data and need that (non-public) data to run.

## Recommended evaluation protocol
1. Split **by die**, never by neuron: neurons of one die share a global process draw. Use 60 / 20 / 20 dies for train / validation / test.
2. Train a healthy-versus-faulty detector, set the threshold at **1 % false reject of healthy validation neurons**, report the **miss rate of faulty test neurons**.
3. Exclude `is_nominal == 1` rows from independent-sample statistics (they are HSPICE's nominal sample, one per deck).
4. Report mean and standard deviation over several random die splits.

## Headline results (details in docs/RESULTS.md)
TSMC 65 nm, faulty neurons missed at 1 % false reject, mean of 6 die splits:

| Readouts | Missed |
|---|---|
| spike train only | 11.4 % +- 2.8 |
| + membrane-voltage readouts | 3.3 % +- 1.3 |
| **+ supply current (charge per spike, peak current)** | **0.0 % +- 0.0** |

The defects hidden from spikes and membrane readouts are devices of the post-spike handshake path (`mna`, `mnb`, `mn2`, `mn3`); the same devices are hidden in GF180.
A single 100 nA pulse with all readouts already reaches 0.1 % missed. Defect location among the 46 classes: 72.6 % (spikes) -> 91.3 % (+Vm) -> 96.2 % (+supply).

## Redistribution and licence status
- **GF180 data and code:** generated with the open GF180MCU PDK (Apache-2.0) and the open-source ngspice. A licence for this
  repository has not been chosen yet; until then all rights are reserved. Contact the authors for reuse.
- **TSMC 65 nm data:** derived from a foundry model library licensed to the institute and therefore not published here.

## Authors and citation
Tushar Dudeja, Vishal Gupta (work toward a test method for analog spiking neurons). Citation text to be added once the release is public.
Version 1.0, generated 2026-10-18.
