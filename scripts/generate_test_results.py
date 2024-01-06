# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import glob
import os
import airflownetwork
import json

files = glob.glob('../examples/23.2/models/*.epJSON')
graph_dir = '../examples/23.2/graphs/'

# Graphs
graph = True
graph_failed = []
if graph:
    for file in files:
        basename = os.path.splitext(os.path.basename(file))[0]
        print(basename)
        model = airflownetwork.load_epjson(file)     
        try:
            auditor = airflownetwork.Auditor(model)
            with open(os.path.join(graph_dir, basename + '.dot'), 'w') as fp:
                auditor.write_dot(fp)
        except Exception as exc:
            graph_failed.append(file)
            print(file, 'failed:', str(exc))


# Audits
audit = False
audit_failed = []
if audit:
    for file in files:
        basename = os.path.splitext(os.path.basename(file))[0]
        #print(basename)
        model = airflownetwork.load_epjson(file)        
        try:
            auditor = airflownetwork.Auditor(model)
            auditor.audit()
            with open(basename + '.json', 'w') as fp:
                json.dump(auditor.json, fp, indent=4)
        except Exception as exc:
            audit_failed.append(file)
            print(file, 'failed:', str(exc))
        else:
            pass
            #print('"%s",' % basename)