# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import sys

if __name__ == '__main__':
    from .cli import airflownetwork

    sys.exit(airflownetwork())
