# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import math

class PowerLaw:
    """Power law flow element.
    
    Parameters
    ----------
    linear: optional
        The linear flow coefficient used in simulation.
    coefficient: optional
        The nonlinear flow coefficient used in simulation.
    exponent: optional
        The nonlinear flow exponent used in simulation.
    """
    def __init__(self, linear:float=0.0, coefficient:float=0.0, exponent:float=0.65):
        self.linear = linear # linear flow coefficient
        self.coefficient = coefficient # nonlinear flow coefficient
        self.exponent = exponent # nonlinear flow exponent

    def type(self):
        """Returns the flow element three-character type.
        
        Returns
        -------
        str:
            The three-character type of the flow element.
        """
        return 'plr'

    def linearize(self, link, multiplier:float=1.0, control:float=1.0):
        """Compute the linear flow coeffient.
        
        The function computes the linear coefficient for use in initialization.
        
        Parameters
        ----------
        link:
            The link object that the linear coefficient is needed for.
        multiplier: optional
            The multiplier determines how many elements this linkage represents. Defaults to 1.
        control: optional
            The control signal that is used to control flow for some elements. Defaults to 1.
        """
        return 0.5 * self.linear * (link.node0.dvisc + link.node1.dvisc)

    def flow(self, link, pdrop:float, multiplier:float=1.0, control:float=1.0):
        """Compute the flow through an element.
        
        Parameters
        ----------
        link:
            The link object that the linear coefficient is needed for.
        pdrop:
            The pressure drop driving the flow.
        multiplier: optional
            The multiplier determines how many elements this linkage represents. Defaults to 1.
        control: optional
            The control signal that is used to control flow for some elements. Defaults to 1.
        """
        upwind = link.node0
        abs_pdrop = pdrop
        sign = 1.0
        if pdrop < 0.0:
            upwind = link.node1
            abs_pdrop = -pdrop
            sign = -1.0
        elif pdrop == 0.0:
            return 1, 0.0, 0.0
        
        cdm = self.linear * upwind.dvisc
        fl = cdm * abs_pdrop
        ft = self.coefficient * upwind.sqrt_density * math.pow(abs_pdrop, self.expt)
        if fl <= ft:
            f = sign*fl
        else:
            f = sign*ft
        return 1, f, 0.0

    def jacobian(self, link, pdrop:float, multiplier:float=1.0, control:float=1.0):
        """Compute the flow through an element and the associated Jacobian terms.
        
        Parameters
        ----------
        link:
            The link object that the linear coefficient is needed for.
        pdrop:
            The pressure drop driving the flow.
        multiplier: optional
            The multiplier determines how many elements this linkage represents. Defaults to 1.
        control: optional
            The control signal that is used to control flow for some elements. Defaults to 1.
        """
        upwind = link.node0
        abs_pdrop = pdrop
        sign = 1.0
        if pdrop < 0.0:
            upwind = link.node1
            abs_pdrop = -pdrop
            sign = -1.0
        elif pdrop == 0:
            df = 0.5 * self.linear * (link.node0.dvisc + link.node1.dvisc)
            return 1, 0.0, 0.0, df, 0.0

        cdm = self.linear * upwind.dvisc
        fl = cdm * abs_pdrop
        ft = self.coefficient * upwind.sqrt_density * math.pow(abs_pdrop, self.exponent)
        if fl <= ft:
            f = sign*fl
            df = cdm
        else:
            f = sign*ft
            df = f * self.exponent / pdrop
        return 1, f, 0.0, df, 0.0
           

class SqrtPowerLaw(PowerLaw):
    """Power law flow element (square root version).
    
    Parameters
    ----------
    linear: optional
        The linear flow coefficient used in simulation.
    coefficient: optional
        The nonlinear flow coefficient used in simulation.
    """
    def __init__(self, linear:float=0.0, ceofficient:float=0.0):
        self.linear = linear # linear flow coefficient
        self.coefficient = ceofficient # nonlinear flow coefficient

    def flow(self, link, pdrop:float, multiplier:float=1.0, control:float=1.0):
        """Compute the flow through the element.
        
        Parameters
        ----------
        link:
            The link object that the linear coefficient is needed for.
        pdrop:
            The pressure drop driving the flow.
        multiplier: optional
            The multiplier determines how many elements this linkage represents. Defaults to 1.
        control: optional
            The control signal that is used to control flow for some elements. Defaults to 1.
        """
        upwind = link.node0
        abs_pdrop = pdrop
        sign = 1.0
        if pdrop < 0.0:
            upwind = link.node1
            abs_pdrop = -pdrop
            sign = -1.0
        elif pdrop == 0.0:
            return 1, 0.0, 0.0
        
        cdm = self.linear * upwind.dvisc
        fl = cdm * abs_pdrop
        ft = self.coefficient * upwind.sqrt_density * math.sqrt(abs_pdrop)
        if fl <= ft:
            f = sign*fl
        else:
            f = sign*ft
        return 1, f, 0.0

    def jacobian(self, link, pdrop:float, multiplier:float=1.0, control:float=1.0):
        """Compute the flow through the element and the associated Jacobian terms.
        
        Parameters
        ----------
        link:
            The link object that the linear coefficient is needed for.
        pdrop:
            The pressure drop driving the flow.
        multiplier: optional
            The multiplier determines how many elements this linkage represents. Defaults to 1.
        control: optional
            The control signal that is used to control flow for some elements. Defaults to 1.
        """
        upwind = link.node0
        abs_pdrop = pdrop
        sign = 1.0
        if pdrop < 0.0:
            upwind = link.node1
            abs_pdrop = -pdrop
            sign = -1.0
        elif pdrop == 0.0:
            df = 0.5 * self.linear * (link.node0.dvisc + link.node1.dvisc)
            return 1, 0.0, 0.0, df, 0.0

        cdm = self.linear * upwind.dvisc
        fl = cdm * abs_pdrop
        ft = self.coefficient * upwind.sqrt_density * math.sqrt(abs_pdrop)
        if fl <= ft:
            f = sign*fl
            df = cdm
        else:
            f = sign*ft
            df = 0.5 * f / pdrop
        return 1, f, 0.0, df, 0.0