# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import math

reference_pressure = 101325.0
reference_temperarure = 20.0
reference_humidity_ratio = 0.0

def energyplus_dynamic_viscosity(temperature:float):
    """Dynamic viscosity of air.

    This is the equation for the dynamic viscosity of air used in EnergyPlus. Origin is unknown.
    
    Parameters
    ----------
    temperature: float
        The air temperature in Celcius.

    Returns
    -------
    float
    """
    return 1.71432e-5 + 4.828e-8 * temperature

def sutherland_dynamic_viscosity(temperature:float):
    """Dynamic viscosity of air.

    Sutherland's equation for the dynamic viscosity of air used in EnergyPlus.
    
    Parameters
    ----------
    temperature: float
        The air temperature in Celcius.

    Returns
    -------
    float
    """
    return 1.458-6 * math.pow(temperature + 273.15, 1.5) / (temperature + 383.55)

def sutherland_kinematic_viscosity(pressure:float, temperature:float, humidity_ratio:float=0.0):
    """Dynamic viscosity of air.

    Sutherland's equation for the dynamic viscosity of air used in EnergyPlus.
    
    Parameters
    ----------
    pressure: float
        The air pressure in Pa.
    temperature: float
        The air temperature in Celcius.
    humidty_ratio: float
        The air humidity ratio.

    Returns
    -------
    float
    """
    density = energyplus_air_density(pressure, temperature, humidity_ratio)
    return 1.458-6 * math.pow(temperature + 273.15, 1.5) / ( density * (temperature + 383.55))

def energyplus_air_density(pressure:float, dry_bulb:float, humidity_ratio:float=0.0):
    """Density of air.

    This is the equation for the density of air used in EnergyPlus.
    
    Parameters
    ----------
    pressure: float
        The air pressure in Pa.
    dry_bulb: float
        The air dry bulb temperature in Celcius.
    humidty_ratio: float
        The air humidity ratio.

    Returns
    -------
    float
    """
    # Van Wylen & Sonntag, Fundamentals of Classical Thermodynamics.
    # ASHRAE handbook 1985 Fundamentals, Ch. 6, eqn. (6),(26)
    return (pressure / (287.0 * (dry_bulb + 273.15) * (1.0 + 1.6077687 * max(humidity_ratio, 1.0e-5))))

density_function = energyplus_air_density
kinematic_viscosity_function = sutherland_kinematic_viscosity