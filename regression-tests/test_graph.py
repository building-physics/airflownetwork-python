# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import airflownetwork

import pytest
import os
import io

@pytest.fixture
def version(request):
    return os.path.join(os.path.dirname(request.module.__file__), '..', 'models', request.param)

def load_graph(filename):
    with open(filename, 'r') as fp:
        return fp.read()

@pytest.mark.parametrize('version', ['23.2'], indirect=True)
def test_RoomAirflowNetwork(version):
    model = airflownetwork.load_epjson(os.path.join(version, 'models', 'RoomAirflowNetwork.epJSON'))
    #graph = load_graph(os.path.join(version, 'graphs', 'RoomAirflowNetworks.dot'))
    auditor = airflownetwork.Auditor(model)
    fake = io.StringIO()
    auditor.write_dot(fake)
    assert str(fake) == ''

@pytest.mark.parametrize('version', ['23.2'], indirect=True)
def test_AirflowNetwork_MultiZone_House(version):
    model = airflownetwork.load_epjson(os.path.join(version, 'models', 'AirflowNetwork_MultiZone_House.epJSON'))
    graph = load_graph(os.path.join(version, 'graphs', 'AirflowNetwork_Multizone_House.dot'))
    auditor = airflownetwork.Auditor(model)
    fake = io.StringIO()
    auditor.write_dot(fake)
    assert fake.getvalue() == graph

@pytest.mark.parametrize('version', ['23.2'], indirect=True)
def test_AirflowNetwork_Simple_SmallOffice(version):
    model = airflownetwork.load_epjson(os.path.join(version, 'models', 'AirflowNetwork_Simple_SmallOffice.epJSON'))
    graph = load_graph(os.path.join(version, 'graphs', 'AirflowNetwork_Simple_SmallOffice.dot'))
    auditor = airflownetwork.Auditor(model)
    fake = io.StringIO()
    auditor.write_dot(fake)
    assert fake.getvalue() == graph

@pytest.mark.parametrize('version', ['23.2'], indirect=True)
def test_AirflowNetwork_Simple_House(version):
    model = airflownetwork.load_epjson(os.path.join(version, 'models', 'AirflowNetwork_Simple_House.epJSON'))
    graph = load_graph(os.path.join(version, 'graphs', 'AirflowNetwork_Simple_House.dot'))
    auditor = airflownetwork.Auditor(model)
    fake = io.StringIO()
    auditor.write_dot(fake)
    assert fake.getvalue() == graph

@pytest.mark.parametrize('version', ['23.2'], indirect=True)
def test_AirflowNetwork_Multizone_SmallOffice(version):
    model = airflownetwork.load_epjson(os.path.join(version, 'models', 'AirflowNetwork_Multizone_SmallOffice.epJSON'))
    graph = load_graph(os.path.join(version, 'graphs', 'AirflowNetwork_Multizone_SmallOffice.dot'))
    auditor = airflownetwork.Auditor(model)
    fake = io.StringIO()
    auditor.write_dot(fake)
    assert fake.getvalue() == graph