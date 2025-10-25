# **Anonymised human location data for urban mobility research**

This repository contains the methodology and results described in:

 Zhong, Chen., et al., Anonymised human location data for urban mobility research. CASA working paper XXX, 2024.


## Abstract

Understanding human mobility is crucial for every aspect of daily life and the functioning of cities. Advanced by sensor technology and the big data economy, a highly influential body of research and applications on human mobility is driven by analyses of massive human location datasets, such as social media data and spending data. New data is emerging as rapidly as evolutionary technologies. Mobile app data is relatively new and has become available only in the recent decade. The derived data products are similar to those mainstreaming existing ones, mainly in trip-activity chains, counts, flow matrices, and derived indicators. However, the data bias varies across areas, periods and policy restrictions, requiring tailored data processing and validation solutions, which are not fully transparently discussed. This study contributes as a handbook for processing similar types of location points data, detailing engineering workflow and multi-stage validation techniques. Second, we present insights into the limitations and potential of data applications that tolerate the inevitable data bias. Finally, open trajectory and matrix data are shared for research purposes. The team will keep updating the methodology and results with the latest developments on GitHub.


## Data Reference Link

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.13327082.svg)](https://doi.org/10.5281/zenodo.13327082)


## Project structure

```
Anonymised_Paper_Private/
├── pyproject.toml          # Project metadata and dependencies
├── src/                    # Main source code
│   ├── process/            # Preprocessing scripts
│   │   ├── preprocess.py   # Main preprocessing pipeline
│   │   └── infomobile.py   # Supporting data processing utilities
│   ├── plots/              # Plotting and analysis scripts
│   │   ├── fig2.py         # Script for figure 2
│   │   ├── fig3_.py        # Script for figure 3
│   │   └── fig4_.py        # Script for figure 4
│   ├── _const.py           # Constants used across scripts
│   └── _plot_utils.py      # Helper functions for plotting
├── notebooks/              # Jupyter notebooks for reproduction and exploration
│   ├── Figures_DataPaper.ipynb  # Main notebook for paper figures
│   ├── fig-4.ipynb         # Notebook for figure 4
│   ├── postraficated.ipynb # Post-stratification workflow
│   └── moving_range.ipynb  # Moving range analysis examples
├── data/                   # Data directory
│   ├── duckdb/             # DuckDB files (intermediate/aggregate database files)
│   └── data4report/        # Prepared files for reports/figures
├── fig/                    # Generated figures (if present)
└── docker/                 # Dockerfiles and environment-related files (optional)
```

## Quick usage

Create and activate a virtual environment from the `pyproject.toml` file using `uv` (or your preferred tool):

```bash
git clone <repository_url>
cd <repository_name>
uv sync  # env synchronization via un
```

- Put any local or restricted datasets into the `data/` directory following the existing structure.
- The data repository contains example and preprocessed files, but some sensitive raw data are intentionally excluded.


## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Citation
If you use this code or data in your research, please cite the original paper:

```
@article{anonymised2024,
  title={Anonymised human location data in England for urban mobility research},
  author={Anonymised, Author and Anonymised, Coauthor},
  journal={Journal Name},
  volume={XX},
  number={YY},
  pages={ZZ-ZZ},
  year={2024},
  publisher={Publisher}
}
