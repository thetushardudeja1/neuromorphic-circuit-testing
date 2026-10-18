# References and tools
Check bibliographic details against the PDFs before any submission; file names refer to the project's `literature/` folder (not redistributed here).

**Circuit and fault model**
- M. El-Sayed, A. Spyrou, D. Pavlidis, E. Afacan, L. Camunas-Mesa, B. Linares-Barranco, H.-G. Stratigopoulos, "Spiking Neuron Hardware-Level Fault Modeling", IOLTS 2020 (`el-sayed-hardware-level-fault-modeling.pdf`).
- T. Serrano-Gotarredona et al., cortical-layer neuromorphic chip, IEEE TCAS-I 2006, Fig. 10 positive event block (`serrano-cortical-layer-2006.pdf`).
- Open-gate fault model: Esen et al., ITC 2016 (`esen-open-defects-itc2016.pdf`).
- M. El-Sayed et al., "Compact Functional Testing for Neuromorphic Computing Circuits", IEEE TCAD 42(7), 2023.
- A. Spyrou et al., "Neuron Fault Tolerance in Spiking Neural Networks", DATE 2021; A. Spyrou, S. Hamdioui, H.-G. Stratigopoulos, "SpikeFI", arXiv:2412.06795; Spyrou and Stratigopoulos, "On-line testing of neuromorphic hardware", ETS 2023; Raptis and Stratigopoulos, DATE 2025.
- Babu et al., "Impact of BTI, HCI and time-zero variability on neuromorphic spike event generation circuits", arXiv:2205.10152.
- Variation: M. Pelgrom et al., "Matching properties of MOS transistors", 1989.

**Tools and models**
- ngspice 41 (open-source circuit simulator); GF180MCU open PDK (GlobalFoundries / Google, Apache-2.0), `sm141064.ngspice`.
- Synopsys HSPICE V-2023.12-SP2; TSMC 65 nm low-power model library `crn65lp_2d5_lk_v1d7` (licensed, not distributed).
- Python 3, pandas, scikit-learn 1.6 (HistGradientBoostingClassifier) for the analyses.

**Prior art still to be read in full before any patent filing** (listed, not yet read): Sunter and Jurga, VTS 2021; Spyrou et al., ETS 2023 (in full); Madge et al., US6787379 and continuation US6943042.
