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
    input_file = os.path.join(this_dir, '..', 'examples', 'law-office-simple.json')
    with afn.temporary_directory():
        with open(input_file, 'r') as fp:
            data = json.load(fp)
        assert data is not None
        model = afn.Model.from_json(data, global_density=1.2040973677927915)
        model.initialize()
        model.air_movement(status_function=print)
        afn.write_results_csv([el for el in model.nodes.values() if el.index is not None], model.links, 'afn.csv')
        assert os.path.exists('afn.csv')
        assert afn.compare_csvs(contam_csv, 'afn.csv', node_density_tolerance=1.0e-8, node_temperature_tolerance=1.0e-5,
                                link_flow_tolerance=1.0e-8, link_pressure_drop_tolerance=2.0e-7) == []
        assert afn.compare_csvs(afn_csv, 'afn.csv', node_tolerance=1.0e-15, link_tolerance=1.0e-15) == []
