# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import json
import sys

infile = sys.argv[1]

with open(infile, 'r') as fp:
    items = json.load(fp)

result = {'title': '',
          'nodes': {},
          'elements': {},
          'links': {}}

for item in items:
    input_type = item.pop('input_type')
    if input_type == 'title':
        result['title'] = item['title']
    elif input_type == 'node':
        name = item.pop('name')
        result['nodes'][name] = item
    elif input_type == 'element':
        name = item.pop('name')
        eltype = item.pop('type')
        if eltype not in result['elements']:
            result['elements'][eltype] = {}
        result['elements'][eltype][name] = item
    elif input_type == 'link':
        name = item.pop('name')
        result['links'][name] = item

print(json.dumps(result, indent=4))
    