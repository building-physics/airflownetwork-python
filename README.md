# AirflowNetwork

[![PyPI - Version](https://img.shields.io/pypi/v/airflownetwork.svg)](https://pypi.org/project/airflownetwork)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/airflownetwork.svg)](https://pypi.org/project/airflownetwork)

-----

**Table of Contents**

- [About](#about)
- [Installation](#installation)
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

## License

`airflownetwork` is distributed under the terms of the [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) license.
