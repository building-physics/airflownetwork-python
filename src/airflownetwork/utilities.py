# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
from contextlib import contextmanager
import tempfile
import os
import csv

@contextmanager
def temporary_directory():
    origin = os.getcwd()
    try:
        tmp = tempfile.TemporaryDirectory()
        os.chdir(tmp.name)
        yield
    finally:
        os.chdir(origin)
        tmp.cleanup()

def compare_nodes(line1:list[str], line2:list[str], pressure_tolerance:float, temperature_tolerance:float,
                  density_tolerance:float, line_number:int):
    messages = []
    # Check names
    if line1[1].strip() != line2[1].strip():
        messages.append('Nodes at line %d have different names: %s, %s' % (line_number, line1[1], line2[1]))
    # Check the time id
    if int(line1[2]) != int(line2[2]):
        messages.append('Nodes at line %d have difference time index: %s, %s' % (line_number, line1[2], line2[2]))
    # Check pressure, temperature, and density
    index = [3, 4, 5]
    vars = ['pressure', 'temperature', 'density']
    tols = [pressure_tolerance, temperature_tolerance, density_tolerance]
    for i,v,t in zip(index,vars,tols):
        delta = abs(float(line1[i]) - float(line2[i]))
        if delta > t:
            messages.append('Nodes at line %d have %s difference %e > %e: %s, %s' % (line_number, v, delta, t, line1[i], line2[i]))
    return messages

def compare_links(line1:list[str], line2:list[str], pressure_drop_tolerance:float, flow_tolerance:float,
                  line_number:int):
    messages = []
    # Check nameslink header,name,time id,pressure drop,flow0,flow1
    if line1[1].strip() != line2[1].strip():
        messages.append('Links at line %d have different names: %s, %s' % (line_number, line1[1], line2[1]))
    # Check the time id
    if int(line1[2]) != int(line2[2]):
        messages.append('Links at line %d have difference time index: %s, %s' % (line_number, line1[2], line2[2]))
    # Check pressure, temperature, and density
    index = [3, 4, 5]
    vars = ['pressure drop', 'flow0', 'flow1']
    tols = [pressure_drop_tolerance, flow_tolerance, flow_tolerance]
    for i,v,t in zip(index,vars,tols):
        delta = abs(float(line1[i]) - float(line2[i]))
        if delta > t:
            messages.append('Links at line %d have %s difference %e > %e: %s, %s' % (line_number, v, delta, t, line1[i], line2[i]))
    return messages

def compare_csvs(csv1:str, csv2:str, node_pressure_tolerance:float=1.0e-7, node_temperature_tolerance:float=1.0e-5,
                 node_density_tolerance:float=1.0e-7, node_tolerance:float|None=None, link_tolerance:float|None=None,
                 link_flow_tolerance:float=1.0e-8, link_pressure_drop_tolerance:float=5.0e-7):
    messages = []
    if node_tolerance is not None:
        node_pressure_tolerance = node_tolerance
        node_temperature_tolerance = node_tolerance
        node_density_tolerance = node_tolerance
    if link_tolerance is not None:
        link_flow_tolerance = link_tolerance
        link_pressure_drop_tolerance = link_tolerance
    with open(csv1) as fp1, open(csv2) as fp2:
        r1 = csv.reader(fp1)
        r2 = csv.reader(fp2)
        line_count = 1
        for line1, line2 in zip(r1, r2):
            # The first column is supposed to be the type of the row
            if line1[0] != line2[0]:
                messages.append('Line %d type mismatch (%s vs %s)' % (line_count, line1[0], line2[0]))
            else:
                if line1[0].endswith('header'):
                    pass
                elif line1[0] == 'node':
                    messages.extend(compare_nodes(line1, line2, node_pressure_tolerance, 
                                                  node_temperature_tolerance, node_density_tolerance, line_count))
                elif line1[0] == 'link':
                    messages.extend(compare_links(line1, line2, link_pressure_drop_tolerance, 
                                                  link_flow_tolerance, line_count))
                else:
                    messages.append('Unknown row type: %s' % line1[0])
            line_count += 1
    return messages