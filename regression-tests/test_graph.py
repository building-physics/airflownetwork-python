import airflownetwork
import itertools

import pytest
import os
import io

versions = ['23.2']
file_basenames = [
    'AirflowNetwork_MultiZone_House',
    'AirflowNetwork_Simple_SmallOffice',
    'RoomAirflowNetwork',
    'AirflowNetwork_Simple_House',
    'AirflowNetwork_Multizone_SmallOffice',
]
parameters = itertools.product(versions, file_basenames)


@pytest.fixture
def version(request):
    return os.path.join(
        os.path.dirname(request.module.__file__), '..', 'examples', request.param
    )


def load_graph(filename):
    with open(filename, 'r') as fp:
        return fp.read()


@pytest.mark.parametrize('version, basename', parameters, indirect=['version'])
def test_example_graphs(version, basename):
    model = airflownetwork.load_epjson(
        os.path.join(version, 'models', basename + '.epJSON')
    )
    graph = load_graph(os.path.join(version, 'graphs', basename + '.dot'))
    auditor = airflownetwork.Auditor(model)
    fake = io.StringIO()
    auditor.write_dot(fake)
    assert fake.getvalue() == graph
