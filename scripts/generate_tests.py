# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import glob
import os
import airflownetwork

files = glob.glob('../models/23.2/models/*.epJSON')

txt = '''

@pytest.mark.parametrize('version', ['23.2'], indirect=True)
def test_%s(version): 
    model = airflownetwork.load_epjson(os.path.join(version, 'models', 'AirflowNetwork_MultiZone_House.epJSON'))
    graph = load_graph(os.path.join(version, 'graphs', 'AirflowNetwork_MultiZone_House.dot'))
    auditor = airflownetwork.Auditor(model)
    fake = io.StringIO()
    auditor.write_dot(fake)
    assert fake.getvalue() == graph

'''

failed = []

for file in files:
    basename = os.path.splitext(os.path.basename(file))[0]
    print(basename)
    model = airflownetwork.load_epjson(file)        
    try:
        auditor = airflownetwork.Auditor(model)
        with open(basename + '.dot', 'w') as fp:
            auditor.write_dot(fp)
    except:
        failed.append(file)
        print(file, 'failed')
    else:
        print(txt % basename)