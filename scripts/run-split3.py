# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import os
import json
import math
import airflownetwork as afn
import matplotlib.pyplot as plt

this_dir = os.path.abspath(os.path.dirname(__file__))
json_file = os.path.join(this_dir, '..', 'examples', 'split3.json')

with open(json_file, 'r') as fp:
    data = json.load(fp)
model = afn.Model.from_json(data)

model.initialize()
iters = model.relax(factor=0.75, status_function=print)
#afn.write_results_csv([el for el in model.nodes.values() if el.index is not None],
#                      model.links, 'steady.csv')
print(iters)
for link in model.links:
    print(link.name, link.flow0)

raise 'STOPSTOPSTOP'

# Modify the model
door_link = None
door_height = 2.25
door_width = 1.25
door_area = door_height*door_width
door_perimeter = 2*(door_width+door_height)
hydraulic_diameter = 4 * door_area / door_perimeter
orf = afn.Orifice(door_area, hydraulic_diameter)
for el in model.links:
    if el.name == 'link-12':
        door_link = el
        break
print(door_link.name, door_link.node0.name, door_link.node1.name)
door_link.element = orf
print('area:', door_area)
print('hydraulic_diameter:', hydraulic_diameter)
print(orf.linear, orf.nonlinear)

for name, node in model.nodes.items():
    print(node.name, node.volume, node.azimuth.degrees)
#ctx.obj.append(ModelContext(model))

# Steady calculation
steady_hour = 12.0
ambient_temperature = ambient_temperature_schedule(steady_hour)
wind_speed = wind_speed_schedule(steady_hour)
wind_direction = wind_direction_schedule(steady_hour)
ambient_pressure = ambient_pressure_schedule(steady_hour)
print('    ambient temperature:', ambient_temperature)
print('       ambient pressure:', ambient_pressure)
print('             wind speed:', wind_speed)
print('         wind direction:', wind_direction.degrees)
# Set all the external node conditions
print('External node pressures:')
for node in model.external_nodes:
    node.temperature = ambient_temperature
    node.pressure = ambient_pressure
    node.wind_pressure_profile = wind_pressure_profile
    dp = node.compute_wind_pressure(wind_speed, wind_direction)
    print(' ',node.name, dp)
model.initialize()
iters = model.relax(factor=0.75, status_function=print)
#afn.write_results_csv([el for el in model.nodes.values() if el.index is not None],
#                      model.links, 'steady.csv')
print(iters, door_link.flow0)

# Quasi-steady calculation
hours = list(range(25))
flows = []
for hour in hours:
    ambient_temperature = ambient_temperature_schedule(hour)
    wind_speed = wind_speed_schedule(hour)
    wind_direction = wind_direction_schedule(hour)
    ambient_pressure = ambient_pressure_schedule(hour)
    # Set all the external node conditions
    for node in model.external_nodes:
        node.temperature = ambient_temperature
        node.pressure = ambient_pressure
        node.wind_pressure_profile = wind_pressure_profile
        node.compute_wind_pressure(wind_speed, wind_direction)
    model.initialize()
    iters = model.relax(factor=0.75, status_function=None)

    #print(hour, iters, door_link.flow0)
    flows.append(door_link.flow0)

minutes = [60*h for h in hours]
plt.scatter(minutes, flows,marker='x', color='black', label='$\\Delta t = 60$ minutes')

minutes = list(range(1441))
flows = []
for minute in minutes:
    hour = float(minute)/60.0
    ambient_temperature = ambient_temperature_schedule(hour)
    wind_speed = wind_speed_schedule(hour)
    wind_direction = wind_direction_schedule(hour)
    ambient_pressure = ambient_pressure_schedule(hour)
    # Set all the external node conditions
    for node in model.external_nodes:
        node.temperature = ambient_temperature
        node.pressure = ambient_pressure
        node.wind_pressure_profile = wind_pressure_profile
        node.compute_wind_pressure(wind_speed, wind_direction)
    model.initialize()
    iters = model.relax(factor=0.75, status_function=None)

    #print(hour, iters, door_link.flow0)
    flows.append(door_link.flow0)

plt.plot(minutes, flows, label='$\\Delta t = 1$ minute')
ax = plt.gca()
ax.set_xlabel('Time (minutes)')
ax.set_ylabel('Door Flow (kg/s)')
ax.legend(loc='lower right')
plt.show()

# Steady calculation
hour = 0.0
ambient_temperature = ambient_temperature_schedule(hour)
wind_speed = wind_speed_schedule(hour)
wind_direction = wind_direction_schedule(hour)
ambient_pressure = ambient_pressure_schedule(hour)
model.initialize()
iters = model.relax(factor=0.75, status_function=print)
#afn.write_results_csv([el for el in model.nodes.values() if el.index is not None],
#                      model.links, 'steady.csv')
print(0, door_link.flow0)
flows = [door_link.flow0]
for minute in range(1, 1441):
    # Get the conditions
    hour = float(minute)/60.0
    ambient_temperature = ambient_temperature_schedule(hour)
    wind_speed = wind_speed_schedule(hour)
    wind_direction = wind_direction_schedule(hour)
    ambient_pressure = ambient_pressure_schedule(hour)
    # Set all the external node conditions
    for node in model.external_nodes:
        node.temperature = ambient_temperature
        node.pressure = ambient_pressure
        node.wind_pressure_profile = wind_pressure_profile
        node.compute_wind_pressure(wind_speed, wind_direction)
    model.unsteady_explicit(60.0)
    flows.append(door_link.flow0)

plt.plot(minutes, flows, label='$\\Delta t = 1$ minute')
ax = plt.gca()
ax.set_xlabel('Time (minutes)')
ax.set_ylabel('Door Flow (kg/s)')
ax.legend(loc='lower right')
plt.show()