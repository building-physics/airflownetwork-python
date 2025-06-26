# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations # Remove when dropping 3.9
import math
import scipy
import numpy as np
from typing import Type
from .powerlaw import PowerLaw, SqrtPowerLaw
from .solver import Solver
#from dataclasses import dataclass

object_lookup = {"plr": PowerLaw, "sqrt_plr": SqrtPowerLaw}

def devnull(msg: str):
    return

class Angle:
    def __init__(self, value:float, units:str):
        self.value = value
        self.units = units
        self.radians = value
        self.degrees = value
        if units == 'degrees':
            self.radians = value*(math.pi/180.0)
        elif units == 'pi_multiplier':
            self.radians = value * math.pi
            self.degrees = value * 90.0
        else: # units == 'radians'
            self.degrees = value*(180.0/math.pi)
    def __float__(self):
        return self.radians


def no_profile(angle:Angle):
    return 0.0

class Node:
    """A class representing a node in the pressure network.
    
    Parameters
    ----------
    name:
        The name of the node.
    variable_pressure:
        Boolean flag that determines whether the pressure is variable.
    height: optional
        The elevation of the node for stack-based pressure calculation.
    temperature: optional
        The temperature of the node.
    pressure: optional
        The pressure of the node.
    index: optional
        The index of the node in the system of equations, only meaningful for variable nodes.
    input_c: optional
        Flag determining the input temperature units. If True, the temperature is in Celcius, otherwise Kelvin.
    azimuth: Angle
    volume: float
    """
    def __init__(self, name:str|None=None, variable_pressure:bool=True, height:float=0.0, temperature:float=293.15,
                 pressure:float=0.0, index:int|None=None, input_c:bool=True, azimuth:Angle|None=None,
                 volume:float=math.inf, wind_pressure_profile=None, **kwargs):
        self.name = name
        self.variable_pressure = variable_pressure
        self.height = height
        self.temperature = temperature
        if input_c:
            self.temperature += 273.15
        self.pressure = pressure
        self.index = index
        self.density = 0.0
        self.viscosity = 0.0
        self.sqrt_density = 0.0
        self.dvisc = 0.0 # Density divided by viscosity
        self.azimuth = azimuth
        if azimuth is None:
            self.azimuth = Angle(math.inf, 'radians')
        self.volume = volume
        if wind_pressure_profile is None:
            self.wind_pressure_profile = no_profile
        else:
            self.wind_pressure_profile = wind_pressure_profile
        self.added_pressure = 0

    def compute_wind_pressure(self, wind_speed:float, wind_direction:Angle):
        angle = wind_direction.degrees - self.azimuth.degrees
        if angle < 0:
            angle += 360.0
        Cp = self.wind_pressure_profile(Angle(angle, 'degrees'))
        self.added_pressure = Cp * 0.5 * self.density * wind_speed * wind_speed
        return self.added_pressure

class Link:
    def __init__(self, name=None, node0=None, height0=0.0, node1=None, height1=0.0, element=None,
                 wind=None, wpmod=0.0, mult=1.0, flipped=False):
        self.name = name
        self.node0 = node0
        self.node1 = node1
        self.ht0 = height0
        self.ht1 = height1
        self.element = element
        self.wind = wind
        self.wpmod = wpmod
        self.multiplier = mult
        self.flipped = flipped
        self.flow0 = 0.0
        self.flow1 = 0.0
        self.pdrop = 0.0

class BadNetwork(Exception):
    """Raised if the network is bad."""
    pass

class Model(Solver):
    """A class containing nodes, links, and other data representing a pressure network.
    """
    def __init__(self, nodes, elements, links, global_temperature:float|None=None, global_density:float|None=None):
        self.nodes = nodes
        self.links = links
        self.elements = elements
        # Handle the network inputs
        for link in links:
            # Flip any links that have node0 as a constant pressure node 
            if not link.node0.variable_pressure:
                if link.node1.variable_pressure:
                    link.node0, link.node1 = link.node1, link.node0
                    link.flipped = True
                else:
                    link.flipped = False
        # Figure out the size of the matrix
        self.variable_nodes = []
        self.external_nodes = []
        count = 0
        for node in self.nodes.values():
            if node.variable_pressure:
                node.index = count
                count += 1
                self.variable_nodes.append(node)
            else:
                self.external_nodes.append(node)
        #assert count == len(self.variable_nodes)
        self.size = count
        row = []
        col = []
        data = []
        for link in self.links:
            if link.node0.variable_pressure:
                # diagonal term
                row.append(link.node0.index)
                col.append(link.node0.index)
                data.append(1.0)
                if link.node1.variable_pressure:
                    # diagonal term
                    row.append(link.node1.index)
                    col.append(link.node1.index)
                    data.append(1.0)
                    # off diagonal terms
                    row.append(link.node0.index)
                    col.append(link.node1.index)
                    data.append(1.0)
                    # off diagonal terms
                    row.append(link.node1.index)
                    col.append(link.node0.index)
                    data.append(1.0)

        matrix = scipy.sparse.coo_matrix((np.array(data, dtype=np.double),
                                          (np.array(row), np.array(col))),
                                          shape=(count, count))
        self.A = scipy.sparse.csr_matrix(matrix)
        self.x = np.zeros([self.size, 1], dtype=np.double)

        self.set_properties(self.nodes.values(), global_temperature=global_temperature,
                            global_density=global_density)

        # Check for disconnected nodes
        problems = []
        for i,el in enumerate(self.A.diagonal()):
            if el < 1:
                for node in self.nodes.values():
                    if node.index == i:
                        problems.append(node)
                        break
        if problems:
           raise BadNetwork('Disconnected nodes found: %s' % ', '.join([el.name for el in problems]))
    
    @classmethod
    def from_json(cls, data:dict, element_lookup:dict = object_lookup, node_object:Type[Node]=Node,
                 link_object:Type[Link]=Link, global_temperature:float|None=None, global_density:float|None=None):
        """Read a model from JSON data.
        
        Parameters
        ----------
        data:
            Input data in JSON format.
            
        Returns
        -------
        Model:
            Model object with the input data.

        Raises
        ------
        BadNetwork:
            Raised if the network is bad.
        """
        global_density = data.get('global_density', global_density)
        global_temperature = data.get('global_temperature', global_temperature)
        nodes = {}
        for name, node in data['nodes'].items():
            if 'azimuth' in node:
                if isinstance(node['azimuth'], dict):
                    node['azimuth'] = Angle(**node['azimuth'])
                else:
                    node['azimuth'] = Angle(node['azimuth'], 'radians')
            nodes[name] = node_object(name=name, **node)
        elements = {}
        for name, el in data['elements']['plr'].items():
            if el['exponent'] == 0.5:
                del el['exponent']
                elements[name] = element_lookup['sqrt_plr'](**el)
            else:
                elements[name] = element_lookup['plr'](**el)
        # Others go here
        links = []
        for name, link in data['links'].items():
            for node_name in ['node0', 'node1']:
                looking_for = link[node_name]
                link[node_name] = nodes.get(looking_for)
                if link['node0'] is None:
                    raise BadNetwork('Failed to find %s named "%s" in link "%s".' % (node_name, looking_for, name))
            looking_for = link['element']
            link['element'] = elements.get(looking_for)
            if link['element'] is None:
                raise BadNetwork('Failed to find element named "%s" in link "%s".' % (looking_for, name))
            links.append(link_object(name=name, **link))
        return cls(nodes, elements, links, global_temperature=global_temperature, global_density=global_density)
        
    def summary(self):
        """Summarize the pressure network in the model.
        
        Returns
        -------
        str:
            A multiline string that describes the model.
        """
        string = 'Title: %s\n\nElements:\n=========\n' % self.title
        elements = {}
        for el in self.elements.values():
            tag = el.type()
            if tag in elements:
                elements[tag] += 1
            else:
                elements[tag] = 1
        for key, value in elements.items():
            string += '%s: %d\n' % (key, value)

        string += '\nNodes: %s\n\nLinks: %s\n' % (len(self.nodes), len(self.links))
        string += '\nSystem size: %d x %x\n' % (len(self.variable_nodes), len(self.variable_nodes))
        return string
    
    def results_summary(self):
        """Summarize the result of simulation of the pressure network.
        
        Returns
        -------
        str:
            A multiline string that describes the results.
        """
        string = 'Title: %s\n\nNodes:\n======\n' % self.title
        for name, node in self.nodes.items():
            nr = node.index
            if nr is None:
                nr = 0
            string += '%4d %s: %e %e %e\n' % (nr, node.name, node.pressure, node.temperature, node.density)
        string += '\n'
    
        string += '\nNodes: %s\n\nLinks: %s\n' % (len(self.nodes), len(self.links))
        string += '\nSystem size: %d x %x\n' % (len(self.variable_nodes), len(self.variable_nodes))
        return string

    def set_properties(self, nodes:list, global_temperature:float|None=None, global_density:float|None=None):
        """Loop and set the properties of the nodes.
        
        Parameters
        ----------
        nodes:
            The list of nodes to modify.
        global_temperature: optional
            If not None, use this temperature everywhere.
        global_density: optional
            If not None, use this density everywhere.
        """
        if global_temperature is None:
            if global_density is None:
                # Compute the full set of properties
                for node in nodes:
                    node.density = 0.0034838*(101325.0+node.pressure)/node.temperature
                    node.sqrt_density = math.sqrt(node.density)
                    node.viscosity = 1.71432e-5 + 4.828E-8 * (node.temperature - 273.15)
                    node.dvisc = node.density / node.viscosity
            else:
                # Set the density everywhere
                for node in nodes:
                    node.density = global_density
                    node.sqrt_density = math.sqrt(node.density)
                    node.viscosity = 1.71432e-5 + 4.828E-8 * (node.temperature - 273.15)
                    node.dvisc = node.density / node.viscosity
        else:
            if global_density is None:
                # Set the temperature everywhere
                for node in nodes:
                    node.temperature = global_temperature
                    node.density = 0.0034838*(101325.0+node.pressure)/node.temperature
                    node.sqrt_density = math.sqrt(node.density)
                    node.viscosity = 1.71432e-5 + 4.828E-8 * (node.temperature - 273.15)
                    node.dvisc = node.density / node.viscosity
            else:
                # Set the temperature and density everywhere
                for node in nodes:
                    node.temperature = global_temperature
                    node.density = global_density
                    node.sqrt_density = math.sqrt(node.density)
                    node.viscosity = 1.71432e-5 + 4.828E-8 * (node.temperature - 273.15)
                    node.dvisc = node.density / node.viscosity

    def stack_pressure_drop(self, link):
        """Compute the stack pressure drop across all the links in the model."""
        # Stack contribution
        sp0 = -9.80 * link.node0.density * link.ht0
        sp1 =  9.80 * link.node1.density * link.ht1
        dhx = (link.node0.height - link.node1.height) + (link.ht0 - link.ht1)
        spx = 0.0
        if dhx != 0.0:
            if link.flow0 > 0.0:
                spx = 9.80 * link.node0.density * dhx
            elif link.flow0 < 0.0:
                spx = 9.80 * link.node1.density * dhx
            else:
                spx = 4.90 * (link.node0.dens + link.node1.dens) * dhx
        return  sp0 + sp1 + spx

    def check_convergence(self, solution, tolerance):
        maxf = max(solution.min(), solution.max(), key=abs)
        return maxf, abs(maxf) <= tolerance
