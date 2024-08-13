# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations # Remove when dropping 3.9
import argparse
import os
import math
import scipy
import numpy
from .powerlaw import PowerLaw, SqrtPowerLaw

object_lookup = {"plr": PowerLaw, "sqrt_plr": SqrtPowerLaw}

def devnull(msg: str):
    return

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
    """
    def __init__(self, name:str|None=None, variable_pressure:bool=True, height:float=0.0, temperature:float=293.15,
                 pressure:float=0.0, index:int|None=None, input_c:bool=True, **kwargs):
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

class Model:
    """A class containing nodes, links, and other data representing a pressure network.
    """
    def __init__(self, nodes, elements, links, global_temperature:float=None, global_density:float=None):
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
        count = 0
        for node in self.nodes.values():
            if node.variable_pressure:
                node.index = count
                count += 1
                self.variable_nodes.append(node)
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

        matrix = scipy.sparse.coo_matrix((numpy.array(data, dtype=numpy.double),
                                          (numpy.array(row), numpy.array(col))),
                                          shape=(count, count))
        self.A = scipy.sparse.csr_matrix(matrix)
        self.x = numpy.zeros([self.size, 1], dtype=numpy.double)

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
    def from_json(cls, data:dict, element_lookup:dict = object_lookup, node_object=Node,
                 link_object=Link, global_temperature:float=None, global_density:float=None):
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
            Raised if the network is bad.
        """
        nodes = {}
        for name, node in data['nodes'].items():
            nodes[name] = node_object(name=name, **node)
        elements = {}
        for name, el in data['elements']['plr'].items():
            if el['exponent'] == 0.5:
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

    def initialize(self, maxiter:int=100):
        """Initialize the flow network.
        
        Compute flows and pressure drops using linear flow representation for all elements.
        
        Parameters
        ----------
        maxiter: optional
            The maximum number of iterations allowed in the solution.
            
        Returns
        -------
        bool:
            True is returned if the initialization has converged in the allowed number of iterations, False otherwise.
        """
        self.A.data.fill(0.0)
        self.x.fill(0.0)
        for link in self.links:
            if link.node0.variable:
                c = link.element.linearize(link)
                # diagonal term
                self.A[link.node0.index, link.node0.index] += c
                if link.node1.variable:
                    # diagonal term
                    self.A[link.node1.index, link.node1.index] += c
                    # off diagonal terms
                    self.A[link.node0.index, link.node1.index] -= c
                    self.A[link.node1.index, link.node0.index] -= c
                else:
                    self.x[link.node0.index] += c*link.node1.pressure
        self.x, info = scipy.sparse.linalg.cg(self.A, self.x, maxiter=maxiter)
        if info == 0:
            # Update the nodal pressures
            for node in self.variable_nodes:
                node.pressure = self.x[node.index]
            # Update the flows:
            for link in self.links:
                c = link.element.linearize(link)
                link.flow0 = c*(link.node0.pressure-link.node1.pressure)
                link.flow1 = 0.0
            return True
        return False
    
    def compute_pressure_drops(self):
        """Compute the pressure drop across all the links in the model."""
        for link in self.links:
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
            # Wind pressure contribution goes here
            link.pdrop =  sp0 + sp1 + spx

    def air_movement(self, maxiter:int=100, max_subiter:int=100, tolerance:float=1.0e-8, status_function=devnull):
        """Compute steady airflows in the model.
        
        Parameters
        ----------
        maxiter: optional
            The maximum number of Newton iterations allowed.
        max_subiter: optional
            The maximum number of conjugate gradient iterations allowed in the linear solve.
        tolerance: optional
            The absolute convergence tolerance.
        status_function: optional
            Function that handles message output, the default is to discard all messages.
        
        Returns
        -------
        int:
            The number of Newton iterations used in the solve.
        """
        self.compute_pressure_drops()
        status_function('iter | Max Resid|\n==== ===============')
        for iter in range(1,maxiter+1):
            self.A.data.fill(0.0)
            self.x.fill(0.0)
            for link in self.links:
                if link.node0.variable:
                    pdrop = link.node0.pressure - link.node1.pressure + link.pdrop
                    nf, link.flow0, link.flow1, df0, df1 = link.element.jacobian(link, pdrop)
                    if nf == 1:
                        # diagonal term
                        self.A[link.node0.index, link.node0.index] += df0
                        self.x[link.node0.index] += link.flow0
                        if link.node1.variable:
                            # diagonal term
                            self.A[link.node1.index, link.node1.index] += df0
                            self.x[link.node1.index] -= link.flow0
                            # off diagonal terms
                            self.A[link.node0.index, link.node1.index] -= df0
                            self.A[link.node1.index, link.node0.index] -= df0
                    else:
                        raise NotImplementedError('Two-way flow is not yet implemented')
            maxf = abs(max(self.x, key=abs))
            
            if abs(maxf) > tolerance:
                status_function('%4d %15.9e' % (iter, maxf))
            else:
                status_function('%4d %15.9e < %e' % (iter, maxf, tolerance))
                # Update the pressure drops, up until now only secondary terms present
                for link in self.links:
                    if link.node0.variable:
                        link.pdrop += link.node0.pressure - link.node1.pressure
                return iter
            info = 0
            self.x, info = scipy.sparse.linalg.cg(self.A, self.x, maxiter=max_subiter)
            if info == 0:
                # Update the nodal pressures, flows are set above
                for node in self.variable_nodes:
                    node.pressure -= self.x[node.index]
            else:
                raise RuntimeError('Newton iteration solve failed at %d iterations' % iter)
        return maxiter

def write_results_csv(nodes, links, csv_file_name: str)   :
    fp = open(csv_file_name, 'w')
    fp.write('node header, name, time id, pressure, temperature, density\n')
    for node in nodes:
        fp.write('node, %s, 0, %21.15e, %21.15e, %21.15e\n' % (node.name, node.pressure,
                                                               node.temperature, node.density))
    fp.write('link header, name, time id, pressure drop, flow0, flow1\n')
    for link in links:
        fp.write('link, %s, 0, %21.15e, %21.15e, %21.15e\n' % (link.name, link.pdrop, link.flow0, link.flow1))
    fp.close()
