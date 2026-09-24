# OuraRing-Pipeline-and-Utility

## Overview

Python-based pipeline for synchronizing Oura wearable data with chronic local field potential (LFP) recordings from the Medtronic Percept deep brain stimulation (DBS) device. For each selected participant and date range, the workflow loads Oura and Percept data from the configured storage locations, aligns measurements across modalities to the nearest available neural timestamp, and exports a synchronized dataset as a CSV for downstream analysis.

This repository accompanies the preprint, *A Reproducible Framework for Integrating Chronic Deep Brain Stimulation Sensing with Wearable Behavioral Monitoring*.

## Installation

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/BCM-Neurosurgery/OuraRing-Pipeline-and-Utility.git
cd OuraRing-Pipeline-and-Utility
```

The required Python environment and dependencies can then be set up using either uv or Conda.

### Option 1: `uv`

If [`uv`](https://docs.astral.sh/uv/) is installed, create the virtual environment and install the dependencies defined in `pyproject.toml` with:

```bash
uv sync
```

### Option 2: Conda

Alternatively, create and activate a Conda environment, then install the required dependencies:

```bash
conda create -n ourasync python=3.14
conda activate ourasync
pip install .
```

## Data Organization

The pipeline expects Oura and Percept LFP data to follow the directory structures shown below. In `config.json`, you can specify the Oura and neural root directories (`oura_dir` and `neural_dir`). `OuraPipeline.py` then constructs the full paths as `oura_path` and `neural_path`. To use a different folder hierarchy, edit these path definitions.

### Oura Data

Oura data should be organized by cohort, patient ID, and date:

```text
<oura_dir>/
└── <cohort>/
    └── <patient>/
        └── oura/
            ├── YYYY-MM-DD/
            ├── YYYY-MM-DD/
            └── ...
```

The expected Oura path is therefore:

```text
<oura_dir>/<cohort>/<patient>/oura/<YYYY-MM-DD>/
```

### Percept LFP Data

Neural data should be organized by cohort and patient:

```text
<neural_dir>/
└── <cohort>/
    └── <patient>/
        └── LFP/
            └── R/
```

The expected neural data path is therefore:

```text
<neural_dir>/<cohort>/<patient>/LFP/R/
```

## Usage

1. Configure `config.json` with your patient IDs, the analysis date ranges for each patient, and the root directories containing the Oura and neural data.

2. The main pipeline then loads and synchronizes the neurobehavioral data for all patients specified in `config.json`. Run this script with:

```bash
# If using uv
uv run python OuraPipeline.py

# If using Conda
python OuraPipeline.py
```

3. (Optional) The preliminary analyses and figures presented in the manuscript can be reproduced using `figures.ipynb`.

## Data Availability

The data supporting the preliminary analyses in this study are available upon request through [DABI](https://dabi.loni.usc.edu/projects/M7FD26LM28KI).

## Citation

If you use this pipeline in your work, please cite:

```bibtex
@Unpublished{Chamarthi2026,
  title   = {A Reproducible Framework for Integrating Chronic Deep Brain
             Stimulation Sensing with Wearable Behavioral Monitoring},
  author  = {Chamarthi, Saipravallika and Reyes, Gabriel and
             Fraczek, Tomasz M. and Pouya, Sophia and Zhou, Yewen and
             Kutcher, Thomas P. and Hanish, Rick R. and Deng, Ashley and
             Herron, Jeffrey A. and Storch, Eric A. and Goodman, Wayne K. and
             Sheth, Sameer A. and Provenza, Nicole R.},
  year    = {2026},
  note    = {medRxiv preprint},
  doi     = {10.64898/2026.09.18.26363453},
  url     = {https://www.medrxiv.org/content/10.64898/2026.09.18.26363453v13}
}
```