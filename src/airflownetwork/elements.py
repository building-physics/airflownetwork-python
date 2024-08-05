# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import airnet
import math
from .eplus import eplus_air_density, eplus_air_viscosity

class Crack:
    def __init__(self, coefficient=0.01, exponent=0.65, reference_density=eplus_air_density(101325.0, 20.0, 0.0),
                 reference_viscosity=eplus_air_viscosity(20.0)):
        self.coefficient = coefficient # Air Mass Flow Coefficient When Window or Door Is Closed [kg/s at 1Pa]
        self.exponent = exponent # Air Mass Flow exponent When Window or Door Is Closed [dimensionless]
        self.reference_density = reference_density  # Reference density for crack data
        self.reference_viscosity = reference_viscosity # Reference viscosity for crack data

    def type(self):
        return 'crk'

    def linearize(self, link):
        VisAve = 0.5 * (link.node0.viscosity + link.node1.viscosity)
        DensAve = 0.5 * (link.node0.density + link.node1.density)
        SqrtDAve = 0.5 * (link.node0.sqrt_density + link.node1.sqrt_density)

        Ctl = (math.pow(self.reference_density / DensAve, self.exponent - 1.0) *
               math.pow(self.reference_viscosity / VisAve, 2.0 * self.exponent - 1.0))
        CDM = self.coefficient * SqrtDAve / VisAve * Ctl

        return CDM
    
    def flow(self, link, pdrop):
        VisAve = 0.5 * (link.node0.viscosity + link.node1.viscosity)
        Tave = 0.5 * (link.node0.temperature + link.node1.temperature)

        sign = 1.0
        upwind = link.node0
        abs_pdrop = pdrop

        if pdrop < 0.0:
            sign = -1.0
            upwind = link.node1
            abs_pdrop = -pdrop

        coef = self.coefficient / upwind.sqrt_density

        # Linear calculation
        RhoCor = (upwind.temperature + 273.15) / (Tave + 273.15)
        Ctl = (math.pow(self.reference_density / upwind.density / RhoCor, self.exponent - 1.0) *
               math.pow(self.reference_viscosity / VisAve, 2.0 * self.exponent - 1.0))
        CDM = coef * upwind.density / upwind.viscosity * Ctl
        FL = CDM * pdrop

        # Nonlinear flow.
        if self.exponent == 0.5:
            abs_FT = coef * upwind.sqrt_density * math.sqrt(abs_pdrop) * Ctl
        else:
            abs_FT = coef * upwind.sqrt_density * math.pow(abs_pdrop, self.exponent) * Ctl
        # Select linear or nonlinear flow.
        if abs(FL) <= abs_FT:
            F0 = FL
        else:
            F0 = sign * abs_FT

        return 1, F0, 0.0

    def jacobian(self, link, pdrop):
        VisAve = 0.5 * (link.node0.viscosity + link.node1.viscosity)
        Tave = 0.5 * (link.node0.temperature + link.node1.temperature)

        sign = 1.0
        upwind = link.node0
        abs_pdrop = pdrop

        if pdrop < 0.0:
            sign = -1.0
            upwind = link.node1
            abs_pdrop = -pdrop

        coef = self.coefficient / upwind.sqrt_density

        # Linear calculation
        RhoCor = (upwind.temperature + 273.15) / (Tave + 273.15)
        Ctl = (math.pow(self.reference_density / upwind.density / RhoCor, self.exponent - 1.0) *
               math.pow(self.reference_viscosity / VisAve, 2.0 * self.exponent - 1.0))
        CDM = coef * upwind.density / upwind.viscosity * Ctl
        FL = CDM * pdrop

        # Nonlinear flow.
        if self.exponent == 0.5:
            abs_FT = coef * upwind.sqrt_density * math.sqrt(abs_pdrop) * Ctl
        else:
            abs_FT = coef * upwind.sqrt_density * math.pow(abs_pdrop, self.exponent) * Ctl
        # Select linear or nonlinear flow.
        if abs(FL) <= abs_FT:
            F0 = FL
            DF0 = CDM
        else:
            F0 = sign * abs_FT
            DF0 = F0 * self.exponent / pdrop

        return 1, F0, 0.0, DF0, 0.0

class SimpleOpening(Crack):
    sqrt2 = 1.414213562
    two_thirds = 2.0/3.0
    gravity = 9.8
    rhoair = 1.2041 # density of standard air
    vsair = 1.81625e-5 # dynamic viscosity of standard air
     
    def __init__(self, coefficient=0.01, exponent=0.65, discharge_coefficient=0.6, min_density_difference=0.0):
        super().__init__(coefficient=coefficient, exponent=exponent, reference_density=self.rhoair,
                         reference_viscosity=self.vsair)
        self.min_density_difference = min_density_difference
        self.discharge_coefficient = discharge_coefficient

    def type(self):
        return 'sop'

    def linearize(self, link):
        return super().linearize(link)
    
    def flow(self, link, pdrop):
        drho = link.node0.density - link.node1.density
        abs_pdrop = abs(pdrop)
        nf = 1

        if abs(drho) < self.min_density_difference:
            return super().calculate(link, pdrop)
        
        gdrho = self.gravity * drho
        Y = pdrop / gdrho
        # F0 = lower flow, FH = upper flow.
        C = self.sqrt2 * link.width * self.discharge_coefficient
        B = C * math.sqrt(abs_pdrop)
        DF0 = B / abs(gdrho)
        # F0 = 0.666667d0 * C * SQRT(ABS(GDRHO * Y)) * ABS(Y)
        F0 = self.two_thirds * B * abs(Y)
        DFH = C * math.sqrt(abs((link.height - Y) / gdrho))
        # FH = 0.666667d0 * DFH * ABS(GDRHO * (Height - Y))
        FH = self.two_thirds * DFH * abs(gdrho * (link.height - Y))

        f0 = f1 = df0 = df1 = 0.0
        if Y <= 0.0:
            # One-way flow(negative).
            if gdrho >= 0.0:
                f0 = -link.node1.sqrt_density * abs(FH - F0)
            else:
                f0 = link.node0.sqrt_density * abs(FH - F0)
    
        elif Y >= link.height:
            # One-way flow(positive).
            if gdrho >= 0.0:
                f0 = link.node0.sqrt_density * abs(FH - F0)
            else:
                f0 = -link.node1.sqrt_density * abs(FH - F0)
        
        else:
            #Two- way flow.
            nf = 2
            if gdrho >= 0.0:
                f0 = -link.node1.sqrt_density * FH
                f1 = link.node0.sqrt_density * F0
            else:
                f0 = link.node0.sqrt_density * FH
                f1 = -link.node1.sqrt_density * F0
        
        return nf, f0, f1
    
    def jacobian(self, link, pdrop):
        drho = link.node0.density - link.node1.density
        abs_pdrop = abs(pdrop)
        nf = 1

        if abs(drho) < self.min_density_difference:
            return super().calculate(link, pdrop)
        
        gdrho = self.gravity * drho
        Y = pdrop / gdrho
        # F0 = lower flow, FH = upper flow.
        C = self.sqrt2 * link.width * self.discharge_coefficient
        B = C * math.sqrt(abs_pdrop)
        DF0 = B / abs(gdrho)
        # F0 = 0.666667d0 * C * SQRT(ABS(GDRHO * Y)) * ABS(Y)
        F0 = self.two_thirds * B * abs(Y)
        DFH = C * math.sqrt(abs((link.height - Y) / gdrho))
        # FH = 0.666667d0 * DFH * ABS(GDRHO * (Height - Y))
        FH = self.two_thirds * DFH * abs(gdrho * (link.height - Y))

        f0 = f1 = df0 = df1 = 0.0
        if Y <= 0.0:
            # One-way flow(negative).
            if gdrho >= 0.0:
                f0 = -link.node1.sqrt_density * abs(FH - F0)
                df0 = link.node1.sqrt_density * abs(DFH - DF0)
            else:
                f0 = link.node0.sqrt_density * abs(FH - F0)
                df0 = link.node0.sqrt_density * abs(DFH - DF0)
    
        elif Y >= link.height:
            # One-way flow(positive).
            if gdrho >= 0.0:
                f0 = link.node0.sqrt_density * abs(FH - F0)
                df0 = link.node0.sqrt_density * abs(DFH - DF0)
            else:
                f0 = -link.node1.sqrt_density * abs(FH - F0)
                df0 = link.node1.sqrt_density * abs(DFH - DF0)
        
        else:
            #Two- way flow.
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

element_lookup = airnet.object_lookup.copy()
element_lookup['crk'] = Crack
element_lookup['sop'] = SimpleOpening