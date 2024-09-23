# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
#from __future__ import annotations # Remove when dropping 3.9
import scipy
import numpy as np

def devnull(msg: str):
    return

class Solver:

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
            if link.node0.variable_pressure:
                c = link.element.linearize(link)
                # diagonal term
                self.A[link.node0.index, link.node0.index] += c
                if link.node1.variable_pressure:
                    # diagonal term
                    self.A[link.node1.index, link.node1.index] += c
                    # off diagonal terms
                    self.A[link.node0.index, link.node1.index] -= c
                    self.A[link.node1.index, link.node0.index] -= c
                else:
                    self.x[link.node0.index] += c*link.node1.pressure
        x, info = scipy.sparse.linalg.cg(self.A, self.x, maxiter=maxiter)
        if info == 0:
            # Update the nodal pressures
            for node in self.variable_nodes:
                node.pressure = x[node.index]
            # Update the flows:
            for link in self.links:
                c = link.element.linearize(link)
                link.flow0 = c*(link.node0.pressure-link.node1.pressure)
                link.flow1 = 0.0
            return True
        return False

    def secondary_pressure_drops(self):
        """Compute the secondary pressure drop across all the links in the model."""
        for link in self.links:
            # Stack contribution
            stack = self.stack_pressure_drop(link)
            # Wind pressure contribution goes here
            link.pdrop =  stack

    def airmov(self, maxiter:int=100, max_subiter:int=100, tolerance:float=1.0e-8, status_function=None):
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
        if status_function is None:
            status_function = devnull
        self.secondary_pressure_drops()
        status_function('iter    max residual\n==== ==================')
        for iter in range(1,maxiter+1):
            self.A.data.fill(0.0)
            self.x.fill(0.0)
            for link in self.links:
                if link.node0.variable_pressure:
                    pdrop = link.node0.pressure - link.node1.pressure + link.pdrop
                    nf, link.flow0, link.flow1, df0, df1 = link.element.jacobian(link, pdrop)
                    if nf == 1:
                        # diagonal term
                        self.A[link.node0.index, link.node0.index] += df0
                        self.x[link.node0.index] += link.flow0
                        if link.node1.variable_pressure:
                            # diagonal term
                            self.A[link.node1.index, link.node1.index] += df0
                            self.x[link.node1.index] -= link.flow0
                            # off diagonal terms
                            self.A[link.node0.index, link.node1.index] -= df0
                            self.A[link.node1.index, link.node0.index] -= df0
                    else:
                        raise NotImplementedError('Two-way flow is not yet implemented')

            maxf, converged = self.check_convergence(self.x, tolerance)
            if converged:
                status_function('%4d |% 15.9e| < %e' % (iter, maxf, tolerance))
                # Update the pressure drops, up until now only secondary terms present
                for link in self.links:
                    if link.node0.variable_pressure:
                        link.pdrop += link.node0.pressure - link.node1.pressure
                return iter
            else:
                status_function('%4d  % 15.9e' % (iter, maxf))
            info = 0
            x, info = scipy.sparse.linalg.cg(self.A, self.x, maxiter=max_subiter)
            if info == 0:
                # Update the nodal pressures, flows are set above
                for node in self.variable_nodes:
                    node.pressure -= x[node.index]
            else:
                raise RuntimeError('Newton iteration solve failed at %d iterations' % iter)
        return maxiter
