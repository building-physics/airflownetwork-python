# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import math
from .properties import energyplus_air_density, sutherland_dynamic_viscosity

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
    def __init__(self, linear:float=0.0, nonlinear:float=0.0, exponent:float=0.65):
        self.linear = linear # linear flow coefficient
        self.nonlinear = nonlinear # nonlinear flow coefficient
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
        return 0.5 * multiplier * control * self.linear * (link.node0.dvisc + link.node1.dvisc)

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
        ft = self.nonlinear * upwind.sqrt_density * math.pow(abs_pdrop, self.exponent)
        return 1, multiplier*control*sign*min(fl, ft), 0.0

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
        ft = self.nonlinear * upwind.sqrt_density * math.pow(abs_pdrop, self.exponent)
        mul = multiplier * control
        if fl <= ft:
            f = mul*sign*fl
            df = mul*cdm
        else:
            f = mul*sign*ft
            df = f * self.exponent / pdrop
        return 1, f, 0.0, df, 0.0
           

class SqrtPowerLaw(PowerLaw):
    """Power law flow element (square root version).
    
    Parameters
    ----------
    linear: float
        The linear flow coefficient used in simulation.
    nonlinear: float
        The nonlinear flow coefficient used in simulation.
    """
    def __init__(self, linear:float, nonlinear:float):
        self.linear = linear # linear flow coefficient
        self.nonlinear = nonlinear # nonlinear flow coefficient

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
        ft = self.nonlinear * upwind.sqrt_density * math.sqrt(abs_pdrop)
        return 1, multiplier*control*sign*min(fl, ft), 0.0

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
        ft = self.nonlinear * upwind.sqrt_density * math.sqrt(abs_pdrop)
        mul = multiplier*control
        if fl <= ft:
            f = mul*sign*fl
            df = mul*cdm
        else:
            f = mul*sign*ft
            df = 0.5 * f / pdrop
        return 1, f, 0.0, df, 0.0
    
class Orifice(SqrtPowerLaw):
    """Orifice flow power law flow element.
    
    Parameters
    ----------
    area: float
        The orifice cross-sectional area.
    hydraulic_diamter: float
        The orifice hydraulic diameter.
    transition_reynolds_number: float
    reference_density: float
    reference_kinematic_viscosity: float
    minimum_transition_pressure_drop: float
    """
    def __init__(self, area:float, hydraulic_diameter:float, discharge_coefficient:float=0.6,
                 transition_reynolds_number:float=30.0,
                 reference_density:float=energyplus_air_density(101325.0, 20.0),
                 reference_kinematic_viscosity:float=sutherland_dynamic_viscosity(20.0)/energyplus_air_density(101325.0, 20.0),
                 minimum_transition_pressure_drop:float=1.0e-10):
        self.area = area
        self.hydraulic_diameter = hydraulic_diameter
        self.discharge_coefficient = discharge_coefficient
        self.transition_reynolds_number = transition_reynolds_number
        nonlinear = math.sqrt(2.0) * discharge_coefficient * area
        w = reference_kinematic_viscosity * reference_density * transition_reynolds_number * math.sqrt(area)
        dPt = (w / (nonlinear * math.sqrt(reference_density)))**2
        dPt = max(dPt, minimum_transition_pressure_drop)
        linear = w * reference_kinematic_viscosity / dPt
        super().__init__(linear, nonlinear)