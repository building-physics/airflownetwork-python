# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import airflownetwork as afn
import json
import os

this_dir = os.path.dirname(os.path.abspath(__file__))

def test_law_office_simple():
    contam_csv = os.path.join(this_dir, 'law-office-simple-3405.csv')
    afn_csv = os.path.join(this_dir, 'law-office-simple-afn.csv')
    net_file = os.path.join(this_dir, '..', 'examples', 'law-office-simple.json')
    with afn.temporary_directory():
        with open(net_file, 'r') as fp:
            data = json.load(fp)
            assert data is not None
        #airnet.run_simulate(net_file, global_density=1.2040973677927915)
        #assert os.path.exists('airnetsim.csv')
        #assert airnet.compare_csvs(contam_csv, 'airnetsim.csv') == []
        #assert airnet.compare_csvs(airnet_csv, 'airnetsim.csv', node_tolerance=1.0e-15) == []
