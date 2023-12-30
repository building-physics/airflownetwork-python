# AirflowNetwork

[![PyPI - Version](https://img.shields.io/pypi/v/airflownetwork.svg)](https://pypi.org/project/airflownetwork)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/airflownetwork.svg)](https://pypi.org/project/airflownetwork)

-----

**Table of Contents**

- [About](#about)
- [Installation](#installation)
- [Checks](#checks)
- [License](#license)

## About
This is a small library of functions and classes to examine EnergyPlus AirflowNetwork models. A driver program is provided to analyze models in the epJSON format. To summarize the model contents:

```
airflownetwork summarize my_model.epJSON
```

To create a graph of the model in the DOT format:

```
airflownetwork graph my_model.epJSON
```

To generate an audit of the model:

```
airflownetwork audit my_model.epJSON
```

Further help is available on the command line:

```
airflownetwork --help
```

## Installation

```console
pip install airflownetwork
```

## Checks

The script checks for a number of issues that may cause an AirflowNetwork to function poorly. These include:

### Link Counts

Models with a large number of links (particularly those with too many links between adjacent zones) may model the building correctly and the simulation results may be correct, but the model performance may be quite poor. A situation that has been observed in user models is the use of individual window elements to model each and every window in a buildings. This may be correct, but as the number of windows increases the performance of the model will suffer, and the performance hit may be avoidable if windows the beahve the same are lumped together. For example, if 10 windows connect a zone to the ambient, but all 10 windows experience the same wind pressure and temperature difference, a single winwdow that represents all 10 will be sufficient and eliminate 9 of the 10 calculations required.

The `audit` command counts the links between zones and flags those that are considered excessive. 

### Connectedness

Models in which there are zones that are "isolated" (i.e., are not connected to the rest of the model via linkages) have been known to be sensitive to convergence issues. For the most part, the solution procedure can handle multiple isolated subnetworks in a single matrix solution, issues that are encountered with these models can be hard to diagnose. The easiest fix to connect together subnetworks is to add one or more linkages very high flow resistance (e.g., a crack element with a very small flow coefficient).

The `audit` command checks that the multizone network (just with surfaces) and the full network (multizone + dsitribution) are fully connected. Models with intrazone features are not currently supported.

## License

`airflownetwork` is distributed under the terms of the [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) license.
