# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import enum
from typing import Self

def urban_function():
    return (0.35, 0.4)

def suburban_function():
    return (0.6, 0.28)

def airport_function():
    return (1.0, 0.15)

class TerrainModifier1993:
    def __init__(self, A0:float, a:float):
        self.A02 = A0**2
        self.two_a = 2 * a
    def wind_pressure(self, Cp:float, density:float, H:float, met:Self, Umet:float, Hmet:float=10.0):
        Ch = self.A02 * (H/Hmet)**self.tow_a
        return 0.5 * density * Umet**2 * Ch * Cp

class TerrainType1993(enum.Enum):
    URBAN = TerrainModifier1993(0.35, 0.4)
    SUBURBAN = TerrainModifier1993(0.6, 0.28)
    AIRPORT = TerrainModifier1993(1.0, 0.15)

class TerrainModifier2005:
    def __init__(self, a:float, delta:float):
        self.a = a
        self.delta = delta
    def local_wind_speed(self, H:float, met:Self, Umet:float, Hmet:float=10.0):
        return Umet * (met.delta/Hmet)**met.a * (H/self.delta)**self.a
    def wind_pressure(self, Cp:float, density:float, H:float, met:Self, Umet:float, Hmet:float=10.0):
        uH = Umet * (met.delta/Hmet)**met.a * (H/self.delta)**self.a
        return 0.5 * Cp * density * uH**2
    
class TerrainType2005(enum.Enum):
    CITY_CENTER = TerrainModifier2005(0.33, 460.0)
    URBAN_AND_SUBURBAN = TerrainModifier2005(0.22, 370.0)
    FEW_OBSTRUCTIONS = TerrainModifier2005(0.14, 270.0)
    UNOBSTRUCTED = TerrainModifier2005(0.1, 210.0)