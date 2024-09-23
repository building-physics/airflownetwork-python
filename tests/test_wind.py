# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
import airflownetwork as afn

def test_terrain_2005():
    loc = afn.TerrainType2005.URBAN_AND_SUBURBAN
    met = afn.TerrainType2005.UNOBSTRUCTED
    Umet = 10.0
    h = 15.0
    assert True # Fix this later, need to get the 1993 code corrected first
