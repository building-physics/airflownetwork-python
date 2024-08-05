# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause

import json
import argparse
import math
import sys
import re

class JsonObject:
    def to_json(self):
        output = {}
        for k,v in vars(self).items():
            if v is not None:
                output[k] = v
        output.pop('name', None)
        return output
    @classmethod
    def from_json(cls, obj):
        new_object = cls()
        v = vars(new_object)
        for key, value in obj.items():
            if key in v:
                v[key] = value
            else:
                raise KeyError('Key input "%s" is unexpected' % key)
        return new_object

class SimpleOpening(JsonObject):
    def __init__(self, name=None, coef=None, CD=0.78, expo=0.5):
        self.name = name
        self.air_mass_flow_coefficient_when_opening_is_closed = coef
        self.air_mass_flow_exponent_when_opening_is_closed = expo
        self.discharge_coefficient = CD
        self.minimum_density_difference_for_two_way_flow = 0.1


class Crack(JsonObject):
    def __init__(self, name=None, coef=None, expo=0.65):
        self.name = name
        self.air_mass_flow_coefficient_at_reference_conditions = coef
        self.air_mass_flow_exponent = expo


def repair_fenestration_surface_detailed(json_object):
    """Rework a fenestration surfaces's vertices."""
    try:
        n = json_object['number_of_vertices']
    except KeyError:
        n = 3
        if 'vertex_4_x_coordinate' in json_object:
            n = 4
    vertices = []
    for i in range(1,n+1):
        x_str = 'vertex_%d_x_coordinate' % i
        y_str = 'vertex_%d_y_coordinate' % i
        z_str = 'vertex_%d_z_coordinate' % i
        x = json_object[x_str]
        y = json_object[y_str]
        z = json_object[z_str]
        #x = json_object.pop(x_str)
        #y = json_object.pop(y_str)
        #z = json_object.pop(z_str)
        vertices.append({'vertex_x_coordinate': x,
                         'vertex_y_coordinate': y,
                         'vertex_z_coordinate': z})
    json_object['vertices'] = vertices


class Vector3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __rmul__(self, other):
        return Vector3D(self.x * other, self.y * other, self.z * other)

    def __truediv__(self, other):
        return Vector3D(self.x / other, self.y / other, self.z / other)

    def dot(self, other):
        return self.x * other.x + self.y * other.y + self.z * other.z

    def mag2(self):
        return self.x * self.x + self.y * self.y + self.z * self.z

    def cross(self, other):
        return Vector3D(self.y * other.z - self.z * other.y,
                        self.z * other.x - self.x * other.z,
                        self.x * other.y - self.y * other.x)


def polygon_area_xy(verts):
    # Need to check that this is at least a triangle
    v_last = verts[-1]
    v = verts[0]
    result = 0.0
    for v_next in verts[1:]:
        result = result + v.x * (v_next.y - v_last.y)
        v_last = v
        v = v_next
    v_next = verts[0]
    result = result + v.x * (v_next.y - v_last.y)
    return 0.5 * result

def polygon_area_zx(verts):
    # Need to check that this is at least a triangle
    v_last = verts[-1]
    v = verts[0]
    result = 0.0
    for v_next in verts[1:]:
        result = result + v.z * (v_next.x - v_last.x)
        v_last = v
        v = v_next
    v_next = verts[0]
    result = result + v.z * (v_next.x - v_last.x)
    return 0.5 * result

def polygon_area_yz(verts):
    # Need to check that this is at least a triangle
    v_last = verts[-1]
    v = verts[0]
    result = 0.0
    for v_next in verts[1:]:
        result = result + v.y * (v_next.z - v_last.z)
        v_last = v
        v = v_next
    v_next = verts[0]
    result = result + v.y * (v_next.z - v_last.z)
    return 0.5 * result


def detailed_area(json_object):
    # Should better check that this is at least a triangle
    #assert len(json_object['vertices']) >= 3, ('Detailed surface only has %d vertices' % len(json_object['vertices']))
    vertices = []
    for v in json_object['vertices']:
        vertices.append(Vector3D(v['vertex_x_coordinate'],
                                 v['vertex_y_coordinate'],
                                 v['vertex_z_coordinate']))
    a = vertices[1] - vertices[0]
    b = vertices[2] - vertices[1]
    c = a.cross(b)
    normal = c / math.sqrt(c.mag2())

    nx = abs(normal.x)
    ny = abs(normal.y)
    nz = abs(normal.z)
    if nx > ny:
        if nx > nz:
            area = polygon_area_yz(vertices)/normal.x
        else:
            area = polygon_area_xy(vertices)/normal.z
    elif ny > nz:
        area = polygon_area_zx(vertices)/normal.y
    else:
        area = polygon_area_xy(vertices)/normal.z
    return area, normal


def tilt_to_elevation(tilt):
    return 90.0 - tilt


def simple_normal(json_object):
    # The Azimuth Angle indicates the direction that the wall faces (outward normal).
    # The angle is specified in degrees where East = 90, South = 180, West = 270, North = 0.
    azimuth = json_object['azimuth'] * math.pi / 180.0
    tilt = json_object.get('tilt', 90.0)
    if tilt == 0.0:
        normal = Vector3D(0.0, 0.0, 1.0)
    elif tilt == 180.0:
        normal = Vector3D(0.0, 0.0, -1.0)
    elif tilt == 90.0:
        normal = Vector3D(math.sin(azimuth),
                          math.cos(azimuth),
                          0.0)
    else:
        elevation = tilt_to_elevation(tilt) * math.pi / 180.0
        normal = Vector3D(math.sin(azimuth) * math.cos(elevation),
                          math.cos(azimuth) * math.cos(elevation),
                          math.sin(elevation))
    return normal


class Surface(JsonObject):
    def __init__(self, name=None, surface_name=None, component_name=None, zone=None,
                 external_node=None, area=None, json=None, other=None, normal=None,
                 parent=None):
        self.name = name
        self.external_node_name = external_node
        self.leakage_component_name = component_name
        self.surface_name = surface_name
        if name is None and surface_name is not None:
            self.name = surface_name + '_AFN'
        self.window_door_opening_factor_or_crack_factor = 0.0
        self.area = area
        self.zone = zone
        self.json = json
        self.normal = normal
        self.parent = parent
        self.other = other
        if other is not None:
            other.other = self
    def to_json(self):
        return {'surface_name': self.surface_name,
                'leakage_component_name': self.component_name,
                'window_door_opening_factor_or_crack_factor': self.window_door_opening_factor_or_crack_factor
                }
                
    @classmethod
    def from_envelope(cls, model, object_type, object_name, object_data, surfaces):
        surface_name = object_name
        area = object_data['length'] * object_data['height']
        zone_name = object_data['zone_name']
        normal = simple_normal(object_data)
        return cls(surface_name=surface_name, area=area, zone=zone_name,
                   json=object_data, normal=normal)
    @classmethod
    def from_partition(cls, model, object_type, object_name, object_data, surfaces):
        surface_name = object_name
        area = object_data['length'] * object_data['height']
        zone_name = object_data['zone_name']
        normal = simple_normal(object_data)
        other_data = model[object_type].get(object_data['outside_boundary_condition_object'], None)
        if other_data is None:
            # Try other zone
            other_zone = model['Zone'].get(object_data['outside_boundary_condition_object'], None)
            if other_zone is None:
                # Report issue?
                return None
            other_surface = cls(zone = other_zone)
        else:
            other_surface_name = object_data['outside_boundary_condition_object']
            other_zone_name = other_data['zone_name']
            other_surface = cls(surface_name=other_surface_name, zone=other_zone_name,
                                json=other_data)
        return cls(surface_name=surface_name, area=area, zone=zone_name,
                   json=object_data, other=other_surface, normal=normal)
    @classmethod
    def from_detailed(cls, model, object_type, object_name, object_data, surfaces):
        surface_name = object_name
        area, normal = detailed_area(object_data)
        area = abs(area)
        zone_name = object_data['zone_name']
        accepted_types = ['Surface', 'Outdoors'] # Might need to add one or more of the coeffs here
        if object_data['outside_boundary_condition'] not in accepted_types:
            return None
        other_surface = None
        if object_data['outside_boundary_condition'] == 'Surface':
            other_data = model[object_type][object_data['outside_boundary_condition_object']]
            other_surface_name = object_data['outside_boundary_condition_object']
            other_zone_name = other_data['zone_name']
            if other_surface_name == surface_name:
                return None
            other_surface = cls(surface_name=other_surface_name, zone=other_zone_name,
                                json=other_data)
        return cls(surface_name=surface_name, area=area, zone=zone_name,
                   json=object_data, other=other_surface, normal=normal)
    @classmethod
    def from_detailed_fenestration(cls, model, object_type, object_name, object_data,
                                   surfaces):
        # This is going to fall down and go boom at some point, will need to
        # refactor to account for the parent holding a lot of the info
        surface_name = object_name
        area, normal = detailed_area(object_data)
        parent_surface_name = object_data['building_surface_name']
        # Look for the parent surface in the surface objects
        parent = None
        for surf in surfaces:
            if surf.surface_name == parent_surface_name:
                parent = surf
                break
            if surf.other is not None:
                if surf.other.surface_name == parent_surface_name:
                    parent = surf
                    break
        assert parent is not None
        zone_name = parent.zone
        other_surface = None
        if 'outside_boundary_condition_object' not in object_data:
            if parent.other is not None:
                other_zone_name = parent.other.zone
                other_surface = cls(zone=other_zone_name)
        else:
            # It's going to be hard to tell if this is properly being handled to
            # avoid doubling up the surfaces, maybe need to rethink approach
            other_surface_name = object_data['outside_boundary_condition_object']
            other_data = model[object_type].get(other_surface_name, None)
            other_zone_name = None
            if other_data is None:
                # This is probably an error, need to verify
                pass
            else:
                other_zone_name = other_data['zone_name'] # Is this really going to work?
                other_surface = cls(surface_name=other_surface_name, zone=other_zone_name)
        return cls(surface_name=surface_name, area=area, zone=zone_name,
                   json=object_data, other=other_surface, normal=normal,
                   parent=parent)


def start_message(mesg):
    sys.stdout.write(mesg)

def message(mesg):
    sys.stdout.write(mesg+'\n')

def complete_message(mesg):
    sys.stdout.write(mesg+'\n')

def post_warning(mesg):
    sys.stdout.write('Warning: '+mesg+'\n')

def silence(mesg):
    pass

def warn_about_objects(model, object_name):
    try:
        count = len(model[object_name])
        post_warning('Model contains %d "%s" objects that will not be simulated' % (count, object_name))
    except KeyError:
        pass

def remove_incompatible_objects(model, object_name):
    try:
        count = len(model[object_name])
        post_warning('Model contains %d "%s" objects that will be removed' % (count, object_name))
        model.pop(object_name)
    except KeyError:
        pass

def build_afn_inputs(model:dict, verbose:bool=False, remove_objects:bool=False, strip:bool=False, no_openings:bool=False, no_windows:bool=False, no_doors:bool=False, 
                     windows_may_be_doors:bool=False, window_filters=None, door_filters=None):
    """Create AirflowNetwork inputs for the input model.
    
    Parameters
    ----------
    model:
        Input model in JSON form.
    verbose: optional
        Operate verbosely and write status messages.
    remove_objects: optional
        Remove incompatible objects.
    strip: optional
        Remove and additional information added to model objects during process.
    no_openings: optional
        Do not add window or door elements.
    no_windows: optional
        Do not add window elements.
    no_doors: optional
        Do not add door elements.
    windows_may_be_doors: optional
        Doors may be represented as windows in the model.
    """

    if window_filters is None:
        window_filters = []

    if door_filters is None:
        door_filters = []

    if not verbose:
        start_message = silence
        message = silence
        complete_message = silence

    # Need to validate right here

    window_objects = ['Window', 'Window:Interzone', 'FenestrationSurface:Detailed']
    door_objects = ['Door', 'GlazedDoor', 'Door:Interzone', 'GlazedDoor:Interzone']

    simple_window_objects = ['Window',
                             'Window:Interzone']
    simple_door_objects = ['Door',
                           'GlazedDoor',
                           'Door:Interzone',
                           'GlazedDoor:Interzone']
    fenestration_objects = ['FenestrationSurface:Detailed']
    simple_wall_objects = ['Wall:Exterior',
                           'Wall:Interzone',
                           #'Wall:Underground',
                           'Wall:Adiabatic']
    simple_envelope_objects = ['Wall:Exterior']
    simple_partition_objects = ['Wall:Interzone',
                                'Wall:Adiabatic']
    simple_roofceiling_objects = ['Roof',
                                  'Ceiling:Adiabatic',
                                  'Ceiling:Interzone']
    simple_roof_objects = ['Roof']
    simple_ceiling_objects = ['Ceiling:Adiabatic',
                              'Ceiling:Interzone']
    simple_floor_objects = ['Floor:Adiabatic',
                            #'Floor:GroundContact',
                            'Floor:Interzone']   
    detailed_wall_objects = ['BuildingSurface:Detailed',
                             'Wall:Detailed']
    detailed_roofceiling_objects = ['RoofCeiling:Detailed']
    detailed_floor_objects = ['Floor:Detailed']

    surface_handler = {'Window': Surface.from_envelope,
                       'Window:Interzone': Surface.from_partition,
                       'Door': Surface.from_envelope,
                       'GlazedDoor': Surface.from_envelope,
                       'Door:Interzone': Surface.from_partition,
                       'GlazedDoor:Interzone': Surface.from_partition,
                       'FenestrationSurface:Detailed': Surface.from_detailed_fenestration}

    windows = {}
    if not (no_windows or no_openings):
        message('Working on window-type objects:')
        for el in window_objects:
            number = 0
            try:
                these_windows = model[el]
                if matchers:
                    matching = []
                    for window in these_windows:
                        for matcher in window_filters:
                            if matcher.search(window['name']):
                                matching.append(window)
                                break
                    these_windows = matching
                number = len(these_windows)
                windows[el] = these_windows
            except:
                pass
            message("\tFound %d '%s' window-type objects" % (number, el))
            if number:
                for name,obj in these_windows.items():
                    message('\t\t%s' % name)

    doors = {}
    if not (no_doors or no_openings):
        message('Working on door-type objects:')
        matchers = []
        
        for el in door_objects:
            number = 0
            try:
                these_doors = model[el]
                if matchers:
                    matching = []
                    for door in these_doors:
                        for matcher in matchers:
                            if matcher.search(door['name']):
                                matching.append(door)
                                break
                    these_doors = matching
                number = len(these_doors)
                doors[el] = these_doors
            except:
                pass
            message("\tFound %d '%s' door-type objects" % (number, el))
            if number:
                for name,obj in these_doors.items():
                    message('\t\t%s' % name)
        if windows_may_be_doors:
            for el in window_objects:
                number = 0
                try:
                    these_doors = model[el]
                    if matchers:
                        matching = {}
                        for name,door in these_doors.items():
                            for matcher in door_filters:
                                if matcher.search(name):
                                    matching[name] = door
                                    break
                        these_doors = matching
                    number = len(these_doors)
                    doors[el] = these_doors
                except:
                    pass
                message("\tFound %d '%s' door-type objects" % (number, el))
                if number:
                    for name,obj in these_doors.items():
                        message('\t\t%s' % name)

    message('Working on envelope surfaces:')

    n_zones = len(model['Zone'])
    interzonal_area = []
    keys = list(model['Zone'].keys())
    zone_lookup = {}
    for i in range(n_zones):
        interzonal_area.append(n_zones*[0.0])
        zone_lookup[keys[i]] = i

    # Handle opaque surfaces
    surfaces = []
    
    for type in simple_envelope_objects:
        count = 0
        for name,obj in model.get(type, {}).items():
            surfaces.append(Surface.from_envelope(model, type, name, obj, None))
            count += 1
        message("\tFound %d '%s' objects" % (count, type))

    for type in simple_partition_objects:
        count = 0
        objects = model.get(type, {})
        keys = list(objects.keys())
        for name in keys:
            obj = model[type][name]
            result = Surface.from_detailed(model, type, name, obj, None)
            surfaces.append(result)
            if result.other is not None:
                keys.remove(result.other.surface_name)
            else:
                count += 1
        message("\tFound %d '%s' objects" % (count, type))

    for type in detailed_wall_objects:
        count = 0
        objects = model.get(type, {})
        keys = list(objects.keys())
        for name in keys:
            obj = model[type][name]
            result = Surface.from_detailed(model, type, name, obj, None)
            if result is not None:
                surfaces.append(result)
                if result.other is not None:
                    keys.remove(result.other.surface_name)
                else:
                    count += 1
        message("\tFound %d '%s' objects" % (count, type))

    message("Done looking for objects.")

    # Split into internal/external surfaces
    envelope_leakage_name = 'Envelope Leakage'
    interzone_leakage_name = 'Interzone Leakage'
    envelope_surfaces = []
    interzone_surfaces = []
    for surf in surfaces:
        if surf.other is not None:
            surf.component_name = interzone_leakage_name
            interzone_surfaces.append(surf)
        else:
            surf.component_name = envelope_leakage_name
            envelope_surfaces.append(surf)

    # Handle window and door surfaces
    envelope_opening_name = 'Envelope Opening'
    interzone_opening_name = 'Interzone Opening'
    interzone_windows = []
    interzone_doors = []
    envelope_windows = []
    envelope_doors = []
    
    if not no_openings:
        # "Fix" the detailed fenestration objects so there's a vertices vector
        if 'FenestrationSurface:Detailed' in windows: # No need to check logical, this will be empty if no_windows
            for obj in windows['FenestrationSurface:Detailed'].values():
                repair_fenestration_surface_detailed(obj)
        if 'FenestrationSurface:Detailed' in doors: # No need to check logical, this will be empty if no_doors
            for obj in doors['FenestrationSurface:Detailed'].values():
                repair_fenestration_surface_detailed(obj)

        # Windows
        allowed_parents = envelope_surfaces + interzone_surfaces
        for type, objects in windows.items():
            for name, obj in objects.items():
                result = surface_handler[type](model, type, name, obj, allowed_parents)
                if result is not None:
                    if result.other is not None:
                        result.component_name = interzone_opening_name
                        interzone_windows.append(result)
                    else:
                        result.component_name = envelope_opening_name
                        envelope_windows.append(result)

        # Doors
        for type, objects in doors.items():
            for name, obj in objects.items():
                result = surface_handler[type](model, type, name, obj, allowed_parents)
                if result is not None:
                    if result.other is not None:
                        result.component_name = interzone_opening_name
                        interzone_doors.append(result)
                    else:
                        result.component_name = envelope_opening_name
                        envelope_doors.append(result)

        # Account for surface areas of openings in parent surfaces
        for opening_surface in interzone_doors + interzone_windows + envelope_doors + interzone_windows:
            if opening_surface.parent is not None:
                new_area = opening_surface.parent.area - opening_surface.area
                assert new_area > 0.0
                opening_surface.parent.area = new_area
            else:
                # Is this an error? Need to verify
                pass


    # Sum up interzone areas
    for surf in interzone_surfaces:
        i = zone_lookup[surf.zone]
        j = zone_lookup[surf.other.zone]
        #print(surf.name,i,j, surf.zone, surf.other.zone)
        interzonal_area[i][j] += surf.area
        interzonal_area[j][i] += surf.area

    max_interzonal_area = 0.0
    for i in range(n_zones):
        for j in range(i+1, n_zones):
            max_interzonal_area = max(max_interzonal_area, interzonal_area[i][j])

    if verbose:
        print(interzonal_area)
        print(max_interzonal_area)

    max_envelope_area = 0.0
    for surf in envelope_surfaces:
        max_envelope_area = max(max_envelope_area, surf.area)

    # Set up the components
    coefficient = 0.01
    envelope_leakage = Crack(name=envelope_leakage_name, coef=coefficient * max_envelope_area)
    interzone_leakage = Crack(name=interzone_leakage_name, coef=2*coefficient * max_interzonal_area)
    envelope_opening = SimpleOpening(name=envelope_opening_name, coef=coefficient)
    interzone_opening = SimpleOpening(name=envelope_opening_name, coef=coefficient)

    # Set up the factors
    for surf in envelope_surfaces:
        surf.window_door_opening_factor_or_crack_factor = surf.area/max_envelope_area
        assert surf.window_door_opening_factor_or_crack_factor > 0.0

    # Set up the factors
    for surf in interzone_surfaces:
        surf.window_door_opening_factor_or_crack_factor = surf.area/max_interzonal_area
        assert surf.window_door_opening_factor_or_crack_factor > 0.0

    # Add to the model
    model['AirflowNetwork:MultiZone:Surface'] = {}
    for obj in envelope_surfaces + interzone_surfaces + interzone_doors + interzone_windows + envelope_doors + envelope_windows:
        model['AirflowNetwork:MultiZone:Surface'][obj.name] = obj.to_json()

    model['AirflowNetwork:MultiZone:Surface:Crack'] = {
        envelope_leakage.name: envelope_leakage.to_json(),
        interzone_leakage.name: interzone_leakage.to_json()
        }

    if not no_openings:
        model['AirflowNetwork:MultiZone:Component:SimpleOpening'] = {
            envelope_opening.name: envelope_opening.to_json(),
            interzone_opening.name: interzone_opening.to_json()
            }

    model['AirflowNetwork:MultiZone:Zone'] = {}
    for name in model['Zone'].keys():
        model['AirflowNetwork:MultiZone:Zone'][name+'_AFN'] = {'zone_name': name}

    # Handle incompatible objects - need to check up on these individual objects
    incompatible_objects = ['ZoneInfiltration:DesignFlowRate',
                            'ZoneInfiltration:EffectiveLeakageArea',
                            'ZoneInfiltration:FlowCoefficient',
                            'ZoneVentilation:DesignFlowRate',
                            'ZoneVentilation:WindandStackOpenArea',
                            #'ZoneAirBalance:OutdoorAir',
                            'ZoneMixing',
                            'ZoneCrossMixing',
                            #'ZoneRefrigerationDoorMixing',
                            'ZoneEarthtube']
                            #'ZoneCoolTower:Shower',
                            #'ZoneThermalChimney',
                            #'ZoneAirMassFlowConservation']

    handle_objects = warn_about_objects
    if remove_objects:
        handle_objects = remove_incompatible_objects
    for obj in incompatible_objects:
        handle_objects(model, obj)

    # Strip out any extra information that got added into the model
    # Right now there there may be a vertices array in FenestrationSurface:Detailed
    if strip:
        fsds = model.get('FenestrationSurface:Detailed', [])
        for name,fsd in fsds.items():
            try:
                fsd.pop('vertices')
            except KeyError:
                pass
