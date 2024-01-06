# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import airflownetwork
import itertools
import json
import pytest
import os

versions = ['23.2']
file_basenames = [
    'AirflowNetwork3zVent',
    'AirflowNetworkAdvanced_SingleSided_NV',
    'AirflowNetworkOccupantVentilationControl',
    'AirflowNetwork_Attic_Duct',
    'AirflowNetwork_Multizone_HorizontalOpening',
    'AirflowNetwork_MultiZone_House',
    'AirflowNetwork_MULTIZONE_House_DuctSizing',
    'AirflowNetwork_MultiZone_House_FanModel',
    'AirflowNetwork_MultiZone_House_OvercoolDehumid',
    'AirflowNetwork_MultiZone_House_TwoSpeed',
    'AirflowNetwork_MultiZone_SmallOffice',
    'AirflowNetwork_MultiZone_SmallOffice_CoilHXAssistedDX',
    'AirflowNetwork_MultiZone_SmallOffice_GenericContam',
    'AirflowNetwork_MultiZone_SmallOffice_HeatRecoveryHXSL',
    'AirflowNetwork_MultiZone_SmallOffice_VAV',
    'AirflowNetwork_PressureControl',
    'AirflowNetwork_Simple_House',
    'AirflowNetwork_Simple_SmallOffice',
    'CrossVent_1Zone_AirflowNetwork',
    'CrossVent_1Zone_AirflowNetwork_with2CrossflowJets',
    'DisplacementVent_Nat_AirflowNetwork',
    'DisplacementVent_Nat_AirflowNetwork_AdaptiveComfort',
    'EMSAirflowNetworkOpeningControlByHumidity',
    'HybridVentilationControl',
    'PythonPluginAirflowNetworkOpeningControlByHumidity',
    'RoomAirflowNetwork',
    'AirflowNetwork3zVentAutoWPC',
    'AirflowNetwork_MultiZone_LocalNode',
    'AirflowNetwork_MultiAirLoops'
]
parameters = itertools.product(versions, file_basenames)


@pytest.fixture
def version(request):
    return os.path.join(
        os.path.dirname(request.module.__file__), '..', 'examples', request.param
    )


def load_audit(filename):
    with open(filename, 'r') as fp:
        return json.load(fp)


@pytest.mark.parametrize('version, basename', parameters, indirect=['version'])
def test_example_audits(version, basename):
    model = airflownetwork.load_epjson(
        os.path.join(version, 'models', basename + '.epJSON')
    )
    audit = load_audit(os.path.join(version, 'audits', basename + '.json'))
    auditor = airflownetwork.Auditor(model)
    auditor.audit()
    assert json.dumps(auditor.json, indent=4) == json.dumps(audit, indent=4)
