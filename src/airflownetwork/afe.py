# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import math

def to_K(T):
    return T + 273.15

def eplus_air_density(pb,  # barometric pressure (Pascals)
                      tdb, # dry bulb temperature (Celsius)
                      dw   # humidity ratio (kgWater/kgDryAir)
    ):
        # FUNCTION INFORMATION:
        #       AUTHOR         G. S. Wright
        #       DATE WRITTEN   June 2, 1994
        #       MODIFIED       na
        #       RE-ENGINEERED  na

        # PURPOSE OF THIS FUNCTION:
        # This function provides density of air as a function of barometric
        # pressure, dry bulb temperature, and humidity ratio.

        # METHODOLOGY EMPLOYED:
        # ideal gas law
        #    universal gas const for air 287 J/(kg K)
        #    air/water molecular mass ratio 28.9645/18.01534

        # REFERENCES:
        # Wylan & Sontag, Fundamentals of Classical Thermodynamics.
        # ASHRAE handbook 1985 Fundamentals, Ch. 6, eqn. (6),(26)

        return (pb / (287.0 * (tdb + 273.15) * (1.0 + 1.6077687 * max(dw, 1.0e-5))))

def eplus_air_viscosity(T # Temperature in Celsius
    ):
        return 1.71432e-5 + 4.828e-8 * T

class PowerLaw:
    def __init__(self, linear = None, coefficient=0.01, exponent=0.65, reference_density=eplus_air_density(101325.0, 20.0, 0.0),
                 reference_viscosity=eplus_air_viscosity(20.0), transition_Re=30.0):
        self.coefficient = coefficient # Air mass flow coefficient [kg/s at 1Pa]
        self.exponent = exponent # Air mass flow exponent [dimensionless]
        self.reference_density = reference_density  # Reference density
        self.reference_kinematic_viscosity = reference_viscosity/reference_density # Reference kinematic viscosity
        if linear is None:
            self.linear = self.compute_linear_coefficient(transition_Re, reference_density, reference_viscosity)

    def type(self):
        return 'plr'

    def compute_linear_coefficient(self, transition_reynum, reference_density, reference_viscosity, dp_min=1.0e-10):
        A = self.coefficient / (0.6 * math.sqrt(2.0))
        F = reference_viscosity * transition_reynum * math.sqrt(A)
        pdrop = max(math.pow(F / (self.coefficient * math.sqrt(reference_density)), 1.0 / self.exponent), dp_min)
        return reference_viscosity * F / (reference_density * pdrop)
    
    def correction(self, node):
        if self.exponent == 0.5:
            return node.sqrt_density
        return math.exp(math.log(self.reference_density / node.density) * (self.exponent - 0.5) +
                        math.log(self.reference_kinematic_viscosity * node.dvisc) * (2.0 * self.exponent - 1.0)) * node.sqrt_density

    def linearize(self, link, multiplier=1.0, control=1.0):
        return control * multiplier * self.linear * 0.5 *(link.node0.dvisc + link.node1.dvisc)

    def flow(self, link, pdrop, multiplier=1.0, control=1.0):
        sign = 1.0
        abs_pdrop = pdrop
        upwind = link.node0
        if pdrop < 0.0:
            sign = -1.0
            abs_pdrop = -pdrop
            upwind = link.node1

        ctrl = control * multiplier
        cdm = self.linear * upwind.dvisc
        abs_Fl = cdm * abs_pdrop

        abs_Ft = 0.0

        if self.exponent == 0.5:
            abs_Ft = self.correction(upwind) * self.coefficient * math.sqrt(abs_pdrop)
        else:
            abs_Ft = self.correction(upwind) * self.coefficient * math.pow(abs_pdrop, self.exponent)

        if abs_Fl <= abs_Ft:
            F0 = sign * abs_Fl * ctrl
        else:
            F0 = sign * abs_Ft * ctrl

        return 1, F0, 0.0

    def jacobian(self, link, pdrop, multiplier=1.0, control=1.0):
        sign = 1.0
        abs_pdrop = pdrop
        upwind = link.node0
        if pdrop < 0.0:
            sign = -1.0
            abs_pdrop = -pdrop
            upwind = link.node1

        ctrl = control * multiplier
        cdm = self.linear * upwind.dvisc
        abs_Fl = cdm * abs_pdrop

        abs_Ft = 0.0

        if self.exponent == 0.5:
            abs_Ft = self.correction(upwind) * self.coefficient * math.sqrt(abs_pdrop)
        else:
            abs_Ft = self.correction(upwind) * self.coefficient * math.pow(abs_pdrop, self.exponent)

        if abs_Fl <= abs_Ft:
            F0 = sign * abs_Fl * ctrl
            DF0 = cdm * ctrl
        else:
            F0 = sign * abs_Ft * ctrl
            DF0 = F0 * self.exponent / pdrop

        return 1, F0, 0.0, DF0, 0.0

class Orifice(PowerLaw):
    sqrt2 = math.sqrt(2.0)
    def __init__(self, linear=None, coefficient=0.01, area=1.0, discharge_coefficient=0.6, 
                 reference_density=eplus_air_density(101325.0, 20.0, 0.0), reference_viscosity=eplus_air_viscosity(20.0)):
        super().__init__(linear=linear, coefficient=coefficient, exponent=0.5, reference_density=reference_density,
                         reference_viscosity=reference_viscosity)
        self.discharge_coefficient = discharge_coefficient
        self.area = area
    
    @classmethod
    def from_data(cls, area, discharge_coefficient=0.6, reference_density=eplus_air_density(101325.0, 20.0, 0.0),
                  reference_viscosity=eplus_air_viscosity(20.0), transition_Re=30.0,
                  minimum_transition_pressure_drop=1.0e-10):
        coefficient = cls.sqrt2 * discharge_coefficient* area
        F = reference_viscosity * transition_Re * math.sqrt(area)
        dPt = (F / (coefficient * math.sqrt(reference_density)))**2
        dPt = max(dPt, minimum_transition_pressure_drop)
        linear = F * reference_viscosity / (dPt * reference_density)

        return cls(linear=linear, coefficient=coefficient, area=area, discharge_coefficient=discharge_coefficient,
                   reference_density=reference_density, reference_viscosity=reference_viscosity)
    
    def type(self):
        return 'orf'

class TwoWayOpening(Orifice):
    two_thirds = 2.0/3.0
    gravity = 9.8
     
    def __init__(self, coefficient=0.01, discharge_coefficient=0.6, height=1.0, width=1.0, reference_density=eplus_air_density(101325.0, 20.0, 0.0),
                 reference_viscosity=eplus_air_viscosity(20.0)):
        super().__init__(coefficient=coefficient, area=height*width, discharge_coefficient=discharge_coefficient,
                         reference_density=reference_density, reference_viscosity=reference_viscosity)
        self.width = width
        self.height = height

    def type(self):
        return 'two'

    def linearize(self, link, multiplier=1.0, control=1.0):
        # Treat as an orifice
        return super().linearize(link, multiplier=multiplier, control=control)
    
    def one_way(self, link, pdrop):
        return abs(link.node0.density - link.node1.density) <= 0.0001 * abs(pdrop)
    
    def control_opening(self, control):
        return self.height, control * self.width
    
    def flow(self, link, pdrop, multiplier=1.0, control=1.0):
        if not self.one_way(self, link, pdrop):
            return super().flow(link, pdrop, multiplier=multiplier, control=control)
        
        drho = link.node0.density - link.node1.density
        abs_pdrop = abs(pdrop)
        nf = 1
        
        local_height, local_width = self.control_opening(control)

        gdrho = self.gravity * drho
        Y = pdrop / gdrho
        # F0 = lower flow, FH = upper flow.
        C = multiplier * self.sqrt2 * local_width * self.discharge_coefficient
        B = C * math.sqrt(abs_pdrop)
        # F0 = 0.666667d0 * C * SQRT(ABS(GDRHO * Y)) * ABS(Y)
        F0 = self.two_thirds * B * abs(Y)
        DFH = C * math.sqrt(abs((local_height - Y) / gdrho))
        # FH = 0.666667d0 * DFH * ABS(GDRHO * (Height - Y))
        FH = self.two_thirds * DFH * abs(gdrho * (local_height - Y))

        f0 = f1 = df0 = df1 = 0.0
        if Y <= 0.0:
            # One-way flow(negative).
            if gdrho >= 0.0:
                f0 = -link.node1.sqrt_density * abs(FH - F0)
            else:
                f0 = link.node0.sqrt_density * abs(FH - F0)
    
        elif Y >= local_height:
            # One-way flow(positive).
            if gdrho >= 0.0:
                f0 = link.node0.sqrt_density * abs(FH - F0)
            else:
                f0 = -link.node1.sqrt_density * abs(FH - F0)
        else:
            #Two-way flow.
            nf = 2
            if gdrho >= 0.0:
                f0 = -link.node1.sqrt_density * FH
                f1 = link.node0.sqrt_density * F0
            else:
                f0 = link.node0.sqrt_density * FH
                f1 = -link.node1.sqrt_density * F0
        
        return nf, f0, f1
    
    def jacobian(self, link, pdrop, multiplier=1.0, control=1.0):
        if not self.one_way(self, link, pdrop):
            return super().calculate(link, pdrop, multiplier=multiplier, control=control)
        
        drho = link.node0.density - link.node1.density
        abs_pdrop = abs(pdrop)
        nf = 1
        
        local_height, local_width = self.control_opening(control)

        gdrho = self.gravity * drho
        Y = pdrop / gdrho
        # F0 = lower flow, FH = upper flow.
        C = multiplier * self.sqrt2 * local_width * self.discharge_coefficient
        B = C * math.sqrt(abs_pdrop)
        DF0 = B / abs(gdrho)
        # F0 = 0.666667d0 * C * SQRT(ABS(GDRHO * Y)) * ABS(Y)
        F0 = self.two_thirds * B * abs(Y)
        DFH = C * math.sqrt(abs((local_height - Y) / gdrho))
        # FH = 0.666667d0 * DFH * ABS(GDRHO * (Height - Y))
        FH = self.two_thirds * DFH * abs(gdrho * (local_height - Y))

        f0 = f1 = df0 = df1 = 0.0
        if Y <= 0.0:
            # One-way flow(negative).
            if gdrho >= 0.0:
                f0 = -link.node1.sqrt_density * abs(FH - F0)
                df0 = link.node1.sqrt_density * abs(DFH - DF0)
            else:
                f0 = link.node0.sqrt_density * abs(FH - F0)
                df0 = link.node0.sqrt_density * abs(DFH - DF0)
    
        elif Y >= local_height:
            # One-way flow(positive).
            if gdrho >= 0.0:
                f0 = link.node0.sqrt_density * abs(FH - F0)
                df0 = link.node0.sqrt_density * abs(DFH - DF0)
            else:
                f0 = -link.node1.sqrt_density * abs(FH - F0)
                df0 = link.node1.sqrt_density * abs(DFH - DF0)
        
        else:
            #Two-way flow.
            nf = 2
            if gdrho >= 0.0:
                f0 = -link.node1.sqrt_density * FH
                df0 = link.node1.sqrt_density * DFH
                f1 = link.node0.sqrt_density * F0
                df1 = link.node0.sqrt_density * DF0
            else:
                f0 = link.node0.sqrt_density * FH
                df0 = link.node0.sqrt_density * DFH
                f1 = -link.node1.sqrt_density * F0
                df1 = link.node1.sqrt_density * DF0
        
        return nf, f0, f1, df0, df1
    
class TwoWayHeightOpening(TwoWayOpening):
    def control_opening(self, control):
        return control * self.height, self.width
    
    def type(self):
        return 'twh'