# SPDX-FileCopyrightText: 2023-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
#
import sys
import math
import re

from .bnd import BranchNodeDetails, NodeConnect

class UnexpectedInput(Exception):
    pass

class BranchNodeDetailsFailure(Exception):
    pass

class UnsupportedObject(Exception):
    pass

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
                raise UnexpectedInput('Key input "%s" is unexpected' % key)
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

class DistributionNode(JsonObject):
    def __init__(self, name=None, component_name_or_node_name=None,
                 component_object_type_or_node_type=None, node_height=3.0):
        self.name = name
        self.component_name_or_node_name = component_name_or_node_name
        self.component_object_type_or_node_type = component_object_type_or_node_type
        self.node_height = node_height

class Linkage(JsonObject):
    def __init__(self, name=None, component_name=None, node_1_name=None, node_2_name=None,
                 thermal_zone_name=None):
        self.name = name
        self.component_name = component_name
        self.node_1_name = node_1_name
        self.node_2_name = node_2_name
        self.thermal_zone_name = thermal_zone_name

class ObjectNode(JsonObject):
    def __init__(self, name=None, type=None):
        self.name = name
        self.component_object_type_or_node_type = type

class RegularNode(JsonObject):
    def __init__(self, name=None, component_name_or_node_name=None):
        self.name = name
        self.component_name_or_node_name = component_name_or_node_name
        self.component_object_type_or_node_type = 'Other'

class DistributionLinkage(JsonObject):
    def __init__(self, name=None, component_name=None, node_1_name=None, node_2_name=None):
        self.name = name
        self.component_name = component_name
        self.node_1_name = node_1_name
        self.node_2_name = node_2_name

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
                #print(parent.name)
                #print(object_data)
                #print(other_data)
                other_parent = None
                other_parent_surface_name = other_data['building_surface_name']
                for surf in surfaces:
                    if surf.surface_name == other_parent_surface_name:
                        other_parent = surf
                        break
                    if surf.other is not None:
                        if surf.other.surface_name == other_parent_surface_name:
                            other_parent = surf
                            break
                assert other_parent is not None
                other_zone = other_parent.zone
                other_surface = cls(surface_name=other_surface_name, zone=other_zone,
                                    parent=other_parent)
        return cls(surface_name=object_name, area=area, zone=zone_name,
                   json=object_data, other=other_surface, normal=normal,
                   parent=parent)

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

opaque_surface_handler = {'BuildingSurface:Detailed': Surface.from_detailed}

opening_surface_handler = {'Window': Surface.from_envelope,
                           'Window:Interzone': Surface.from_partition,
                           'Door': Surface.from_envelope,
                           'GlazedDoor': Surface.from_envelope,
                           'Door:Interzone': Surface.from_partition,
                           'GlazedDoor:Interzone': Surface.from_partition,
                           'FenestrationSurface:Detailed': Surface.from_detailed_fenestration}

surface_handler = opaque_surface_handler | opening_surface_handler

def check_supported_surfaces():
    objects = (window_objects + door_objects + simple_window_objects
               + simple_door_objects + fenestration_objects + simple_wall_objects
               + simple_envelope_objects + simple_partition_objects + simple_roofceiling_objects
               + simple_roof_objects + simple_ceiling_objects + simple_floor_objects
               + detailed_wall_objects + detailed_roofceiling_objects + detailed_floor_objects)
    for name in set(objects):
        if name not in surface_handler:
            print('- ' + name + ' is not currently supported')
        else:
            print('+ ' + name + ' is supported')

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

def delete_objects(model, object_name):
    try:
        count = len(model[object_name])
        post_warning('Model contains %d "%s" objects that will be removed' % (count, object_name))
        model.pop(object_name)
    except KeyError:
        pass

def filter_objects(matchers, objects):
    keep = []
    toss = []
    for obj in objects:
        name = obj.surface_name
        for matcher in matchers:
            if matcher.search(name):
                keep.append(obj)
                break
        else:
            toss.append(obj)
    return keep, toss

def filter_other_objects(matchers, objects):
    keep = []
    toss = []
    for obj in objects:
        name = obj.surface_name
        other_name = obj.other.surface_name
        for matcher in matchers:
            if matcher.search(name) or matcher.search(other_name):
                keep.append(obj)
                break
        else:
            toss.append(obj)
    return keep, toss

class ZoneConnect:
    def __init__(self, inlet=None, node=None, outlet=None):
        self.inlet = inlet
        self.node = node
        self.outlet = outlet
    def valid(self):
        return self.inlet is not None and self.node is not None and self.outlet is not None

class ComponentConnect:
    def __init__(self, inlet=None, outlet=None):
        self.inlet = inlet
        self.outlet = outlet
    def valid(self):
        return self.inlet is not None and self.outlet is not None
    def to_linkage(self):
        pass

class SplitterConnect:
    def __init__(self, inlet=None, outlet=None):
        self.inlet = inlet
        self.outlets = []
        if outlet is not None:
            self.outlets = [outlet]
    def valid(self):
        return self.inlet is not None and self.outlet is not None
    @property
    def outlet(self):
        if not self.outlets:
            return None
        return self.outlets[0]
    @outlet.setter
    def outlet(self, outlet):
        self.outlets.append(outlet)
    def to_linkage(self):
        pass

class MixerConnect:
    def __init__(self, inlet=None, outlet=None):
        self.inlets = []
        if inlet is not None:
            self.inlets = [inlet]
        self.outlet = outlet
    def valid(self):
        return self.inlet is not None and self.outlet is not None
    @property
    def inlet(self):
        if not self.inlets:
            return None
        return self.inlets[0]
    @inlet.setter
    def inlet(self, inlet):
        self.inlets.append(inlet)
    def to_linkage(self):
        pass

equivalent_lookup = {
    'AIRTERMINAL:SINGLEDUCT:CONSTANTVOLUME:REHEAT': 'AirflowNetwork:Distribution:Component:TerminalUnit',
    'AIRTERMINAL:SINGLEDUCT:CONSTANTVOLUME:NOREHEAT': 'AirflowNetwork:Distribution:Component:Duct',
    'AIRTERMINAL:SINGLEDUCT:VAV:REHEAT': 'AirflowNetwork:Distribution:Component:TerminalUnit',
    'AIRTERMINAL:SINGLEDUCT:VAV:NOREHEAT': 'AirflowNetwork:Distribution:Component:Duct',
    'HEATEXCHANGER:AIRTOAIR:FLATPLATE': 'AirflowNetwork:Distribution:Component:HeatExchanger',
    'HEATEXCHANGER:AIRTOAIR:SENSIBLEANDLATENT': 'AirflowNetwork:Distribution:Component:HeatExchanger',
    'HEATEXCHANGER:DESICCANT:BALANCEDFLOW': 'AirflowNetwork:Distribution:Component:HeatExchanger',
    'COIL:COOLING:DX': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:COOLING:DX:SINGLESPEED': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:COOLING:DX:TWOSPEED': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:HEATING:FUEL': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:HEATING:ELECTRIC': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:HEATING:DX:SINGLESPEED': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:COOLING:WATER': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:HEATING:WATER': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:COOLING:WATER:DETAILEDGEOMETRY': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:COOLING:DX:TWOSTAGEWITHHUMIDITYCONTROLMODE': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:COOLING:DX:MULTISPEED': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:HEATING:DX:MULTISPEED': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:HEATING:DESUPERHEATER': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:HEATING:ELECTRIC:MULTISTAGE': 'AirflowNetwork:Distribution:Component:Coil',
    'COIL:HEATING:GAS:MULTISTAGE': 'AirflowNetwork:Distribution:Component:Coil',
    'FAN:CONSTANTVOLUME': 'AirflowNetwork:Distribution:Component:Fan',
    'FAN:ONOFF': 'AirflowNetwork:Distribution:Component:Fan',
    'FAN:VARIABLEVOLUME': 'AirflowNetwork:Distribution:Component:Fan',
    'FAN:SYSTEMMODEL': 'AirflowNetwork:Distribution:Component:Fan'
    }

def default_fan(object_name=None, object_type=None):
    return {'fan_name': object_name,
            'supply_fan_object_type': object_type}

def default_coil(object_name=None, object_type=None, length=0.1, hydraulic_diameter=0.5):
    return {'coil_name': object_name,
            'coil_object_type': object_type,
            'air_path_length': length,
            'air_path_hydraulic_diameter': hydraulic_diameter}

def default_hx(object_name=None, object_type=None, length=0.1, hydraulic_diameter=0.5):
    return {'heatexchanger_name': object_name,
            'heatexchanger_object_type': object_type,
            'air_path_length': length,
            'air_path_hydraulic_diameter': hydraulic_diameter}

def default_tu(object_name=None, object_type=None, length=0.1, hydraulic_diameter=0.5):
    return {'terminal_unit_name': object_name,
            'terminal_unit_object_type': object_type,
            'air_path_length': length,
            'air_path_hydraulic_diameter': hydraulic_diameter}

def default_duct(object_name=None, object_type=None, length=0.1, hydraulic_diameter=0.5, cross_section_area=0.25):
    return {'duct_length': length,
            'hydraulic_diameter': hydraulic_diameter,
            'cross_section_area': cross_section_area}

equivalent_handler = {'AirflowNetwork:Distribution:Component:Fan': default_fan,
                      'AirflowNetwork:Distribution:Component:Coil': default_coil,
                      'AirflowNetwork:Distribution:Component:HeatExchanger': default_hx,
                      'AirflowNetwork:Distribution:Component:TerminalUnit': default_tu,
                      'AirflowNetwork:Distribution:Component:Duct': default_duct}

class NetworkBuilder:
    def __init__(self, model, **kwargs):
        self.model = model
        self.model_windows = kwargs.get('model_windows', True) # Model windows
        self.window_patterns = kwargs.get('window_patterns', []) # Patterns used to find windows
        self.model_doors = kwargs.get('model_doors', True) # Model doors
        self.door_patterns = kwargs.get('door_patterns', []) # Patterns used to find doors
        self.model_envelope =kwargs.get('model_envelope', True) # Model envelope
        self.door_windows = kwargs.get('door_windows', True) # Doors may be window-type objects

        self.envelope_leakage_name = kwargs.get('envelope_leakage_name','Envelope Leakage')
        self.interzone_leakage_name = kwargs.get('interzone_leakage_name', 'Interzone Leakage')
        self.envelope_window_name = kwargs.get('envelope_window_name','Envelope Window')
        self.interzone_window_name = kwargs.get('interzone_window_name', 'Interzone Window')
        self.envelope_door_name = kwargs.get('envelope_door_name','Envelope Door')
        self.interzone_door_name = kwargs.get('interzone_door_name', 'Interzone Door')

        self.verbose = kwargs.get('verbose', False)
        self.aggregate = kwargs.get('aggregate', False)

    def process_surfaces(self):
        # Process the surfaces of the model. This is needed even for models with only
        # windows and doors because we want the base surfaces.
        message('Working on parent surface objects:')
        self.surfaces = []
    
        for type in simple_envelope_objects: # These should not have an other side surface, need to do something here on that
            surfs = []
            message("\tWorking on '%s' objects..." % type)
            for name,obj in self.model.get(type, {}).items():
                result = surface_handler[type](self.model, type, name, obj, None)
                surfs.append(result)
            message("\tConverted %d '%s' objects" % (len(surfs), type))
            if self.verbose:
                for surf in surfs:
                    message('\t\t%s' % surf.name)
            self.surfaces.extend(surfs)

        for type in simple_partition_objects: # These objects are assumed to be internal partitions
            surfs = []
            objects = self.model.get(type, {})
            keys = list(objects.keys())
            message("\tWorking on '%s' objects..." % type)
            for name in keys:
                obj = self.model[type][name]
                result = surface_handler[type](self.model, type, name, obj, None)
                self.surfaces.append(result)
                if result.other is not None: # Need to review the return None bit, maybe just raise
                    keys.remove(result.other.surface_name)
            message("\tConverted %d '%s' objects" % (len(surfs), type))
            if self.verbose:
                for surf in surfs:
                    message('\t\t%s' % surf.name)
            self.surfaces.extend(surfs)

        for type in detailed_wall_objects: # These could be either
            surfs = []
            objects = self.model.get(type, {})
            keys = list(objects.keys())
            message("\tWorking on '%s' objects..." % type)
            for name in keys:
                obj = self.model[type][name]
                result = surface_handler[type](self.model, type, name, obj, None)
                if result is not None: # Need to review the return None bit, maybe just raise
                    surfs.append(result)
                    if result.other is not None:
                        keys.remove(result.other.surface_name)
            message("\tConverted %d '%s' objects" % (len(surfs), type))
            if self.verbose:
                for surf in surfs:
                    if surf.other is not None:
                        message('\t\t%s (%s)' % (surf.name, surf.other.name))
                    else:
                        message('\t\t%s' % surf.name)
            self.surfaces.extend(surfs)

        message("Done looking for parent surface objects.")

        # Split into internal/external surfaces
        start_message('Categorizing surfaces... ')
        self.envelope_surfaces = []
        self.interzone_surfaces = []
        self.roof_surfaces = []
        self.other_surfaces = []
        for surf in self.surfaces:
            if surf.other is not None:
                self.other_surfaces.append(surf.other)
                surf.component_name = self.interzone_leakage_name
                self.interzone_surfaces.append(surf)
            else:
                if self.model_envelope:
                    surf.component_name = self.envelope_leakage_name
                    self.envelope_surfaces.append(surf)
        complete_message('Done.')

        # Work on subsurfaces
        message('Working on subsurface objects:')
        self.windows = []
        self.doors = []
        self.interzone_doors = []
        self.interzone_windows = []
        self.envelope_doors = []
        self.envelope_windows = []
        window_matchers = []
        if self.model_windows:
            for pattern in self.window_patterns:
                window_matchers.append(re.compile(pattern))
        door_matchers = []
        if self.model_doors:
            for pattern in self.door_patterns:
                door_matchers.append(re.compile(pattern))
        # Handle the window objects
        if self.model_windows or (self.model_doors and self.door_windows):
            # "Fix" the detailed fenestration objects so there's a vertices vector
            for obj in self.model.get('FenestrationSurface:Detailed',{}).values():
                repair_fenestration_surface_detailed(obj)
            allowed_parents = self.surfaces  # self.envelope_surfaces + self.interzone_surfaces
            for type in window_objects:
                isurfs = []
                esurfs = []
                keys = list(self.model.get(type, {}).keys())
                message("\tWorking on '%s' objects..." % type)
                for name in keys:
                    obj = self.model[type][name]
                    result = surface_handler[type](self.model, type, name, obj, allowed_parents)
                    if result is not None: # Need to check on this return
                        surfs.append(result)
                        if result.other is not None:
                            #if self.model_windows:
                            #    if window_matchers:
                            #        for matcher in window_matchers:
                            #            if matcher.search(name):
                            #                result.component_name = self.interzone_window_name
                            #    else:    
                            #        result.component_name = self.interzone_window_name
                            keys.remove(result.other.surface_name)
                            isurfs.append(result)
                        else:
                            #if self.model_windows:
                            #    if window_matchers:
                            #        for matcher in window_matchers:
                            #            if matcher.search(name):
                            #                result.component_name = self.interzone_window_name
                            #    else:
                            #        result.component_name = self.envelope_window_name
                            esurfs.append(result)
                self.interzone_windows.extend(isurfs)
                self.envelope_windows.extend(esurfs)
                message("\tConverted %d '%s' objects" % (len(isurfs) + len(esurfs), type))
                if self.verbose:
                    for surf in isurfs:
                        message('\t\t%s (%s)' % (surf.surface_name, surf.other.surface_name))
                    for surf in esurfs:
                        message('\t\t%s' % surf.surface_name)
                
            self.windows = self.envelope_windows + self.interzone_windows

        if self.model_doors:
            # Find all of the surfaces and convert them
            for type in door_objects:
                isurfs = []
                esurfs = []
                message("\tWorking on '%s' objects..." % type)
                for name, obj in self.model.get(type, {}).items():
                    result = surface_handler[type](self.model, type, name, obj, allowed_parents)
                    if result is not None: # Need to check on this return
                        if result.other is not None:
                            self.interzone_doors.append(result)
                        else:
                            self.envelope_doors.append(result)
                self.interzone_doors.extend(isurfs)
                self.envelope_doors.extend(esurfs)
                message("\tConverted %d '%s' objects" % (len(isurfs) + len(esurfs), type))
                if self.verbose:
                    for surf in isurfs:
                        message('\t\t%s (%s)' % (surf.surface_name, surf.other.surface_name))
                    for surf in esurfs:
                        message('\t\t%s' % surf.surface_name)
            self.doors = self.interzone_doors + self.envelope_doors

            # Apply the filters if we have them
            if door_matchers:
                self.interzone_doors = filter_other_objects(door_matchers, self.interzone_doors)[0]
                self.envelope_doors = filter_objects(door_matchers, self.envelope_doors)[0]
                if self.door_windows:
                    iz_d, self.interzone_windows = filter_other_objects(door_matchers, self.interzone_windows)
                    self.interzone_doors.extend(iz_d)
                    e_d, self.envelope_windows = filter_objects(door_matchers, self.envelope_windows)
                    self.envelope_doors.extend(e_d)

            if not self.model_windows:
                self.interzone_windows = []
                self.envelope_windows = []
            elif window_matchers:
                self.interzone_windows = filter_other_objects(window_matchers, self.interzone_windows)[0]
                self.envelope_windows = filter_objects(window_matchers, self.envelope_windows)[0]

        message('Done looking for subsurface objects.')
        if self.model_windows or self.model_doors:
            start_message('Setting opening components... ')
            for surf in self.interzone_doors:
                surf.component_name = self.interzone_door_name
            for surf in self.envelope_doors:
                surf.component_name = self.envelope_door_name
            for surf in self.interzone_windows:
                surf.component_name = self.interzone_window_name
            for surf in self.envelope_windows:
                surf.component_name = self.envelope_window_name
            complete_message('Done.')
        
    def create_network(self):
        # Adjust areas if there are subsurfaces involved
        for surf in self.interzone_doors + self.envelope_doors + self.interzone_windows + self.envelope_windows:
            new_area = surf.parent.area - surf.area
            assert new_area > 0.0
            surf.parent.area = new_area
        # The max area step is necessary because of the current limitations of the
        # multiplier in AFN
        max_envelope_area = 0.0
        for surf in self.envelope_surfaces:
            max_envelope_area = max(max_envelope_area, surf.area)
        if self.aggregate:
            # Set up a matrix and a lookup table to help aggregate surfaces
            n_zones = len(self.model['Zone'])
            interzonal_area = []
            keys = list(self.model['Zone'].keys())
            zone_lookup = {}
            for i in range(n_zones):
                interzonal_area.append(n_zones*[0.0])
                zone_lookup[keys[i]] = i

            # Compute the areas between zones and select representative link
            linked = []
            representative = []
            for surf in self.interzone_surfaces:
                i = zone_lookup[surf.zone]
                j = zone_lookup[surf.other.zone]
                link = {i,j}
                if link not in linked:
                    linked.append(link)
                    representative.append(surf)
                #print(surf.name,i,j, surf.zone, surf.other.zone)
                interzonal_area[i][j] += surf.area
                interzonal_area[j][i] += surf.area
            # Get the maximum, probably are better ways to do this
            max_interzone_area = 0.0
            for i in range(n_zones):
                for j in range(i+1, n_zones):
                    max_interzone_area = max(max_interzone_area, interzonal_area[i][j])
            # The list of representative surfaces is now the interzonal surfaces list
            self.interzone_surfaces = representative
            for link, surf in zip(linked, self.interzone_surfaces):
                link = list(link)
                surf.area = interzonal_area[link[0]][link[1]]
        else:
            max_interzone_area = 0.0
            for surf in self.interzone_surfaces:
                max_interzone_area = max(max_interzone_area, surf.area)

        # Report out areas
        message('Maximum interzone area is %s' % str(max_interzone_area))
        message(' Maximum envelope area is %s' % str(max_envelope_area))

        # Set up the components
        coefficient = 0.01
        cracks = {}
        if self.envelope_surfaces:
            cracks[self.envelope_leakage_name] = Crack(name=self.envelope_leakage_name, coef=coefficient * max_envelope_area).to_json()
        if self.interzone_surfaces:
            cracks[self.interzone_leakage_name] = Crack(name=self.interzone_leakage_name, coef=2 * coefficient * max_envelope_area).to_json()

        simple_openings = {}
        if self.envelope_doors:
            simple_openings[self.envelope_door_name] = SimpleOpening(name=self.envelope_door_name, coef=coefficient).to_json()
        if self.interzone_doors:
            simple_openings[self.interzone_door_name] = SimpleOpening(name=self.interzone_door_name, coef=2*coefficient).to_json()
        if self.envelope_windows:
            simple_openings[self.envelope_window_name] = SimpleOpening(name=self.envelope_window_name, coef=coefficient).to_json()
        if self.interzone_windows:
            simple_openings[self.interzone_window_name] = SimpleOpening(name=self.interzone_window_name, coef=2*coefficient).to_json()

        # Set up the factors
        for surf in self.envelope_surfaces:
            surf.window_door_opening_factor_or_crack_factor = surf.area/max_envelope_area
            assert surf.window_door_opening_factor_or_crack_factor > 0.0
        for surf in self.interzone_surfaces:
            surf.window_door_opening_factor_or_crack_factor = surf.area/max_interzone_area
            assert surf.window_door_opening_factor_or_crack_factor > 0.0

        # Add to the model
        self.model['AirflowNetwork:MultiZone:Surface'] = {}
        for obj in self.envelope_surfaces + self.interzone_surfaces + self.interzone_doors + self.interzone_windows + self.envelope_doors + self.envelope_windows:
            self.model['AirflowNetwork:MultiZone:Surface'][obj.name] = obj.to_json()

        if cracks:
            self.model['AirflowNetwork:MultiZone:Surface:Crack'] = cracks

        if simple_openings:
            self.model['AirflowNetwork:SimpleOpening'] = simple_openings

        self.model['AirflowNetwork:MultiZone:Zone'] = {}
        for name in self.model['Zone'].keys():
            self.model['AirflowNetwork:MultiZone:Zone'][name+'_AFN'] = {'zone_name': name}

    def surface_stats(self):
        string = 'Surface Statistics\n'
        string += '   Envelope surfaces: %d\n' % len(self.envelope_surfaces)
        string += '  Interzone surfaces: %d\n' % len(self.interzone_surfaces)
        string += ' Other side surfaces: %d\n' % len(self.other_surfaces)
        string += '  Multizone surfaces: %d\n' % len(self.surfaces)
        string += '\nSuburface Statistics\n'
        string += '    Envelope windows: %d\n' % len(self.envelope_windows)
        string += '   Interzone windows: %d\n' % len(self.interzone_windows)
        string += '      Envelope doors: %d\n' % len(self.envelope_doors)
        string += '     Interzone doors: %d\n' % len(self.interzone_doors)
        return string
    
    def build_distribution(self, bnd):
        zone_connects={}
        component_connects={}
        oasys_connects={}
        zonesplitter_connects={}
        zonemixer_connects={}
        for c in bnd.node_connections:
            if c.is_parent:
                continue
            # Sort out the connections into the sets that we need
            print(c.connection_type)
            # Use case for this when it's supported by all the live versions of Python
            if c.connection_type is NodeConnect.ZoneInlet:
                if c.object_name in zone_connects:
                    zone_connects[c.object_name].inlet = c
                else:
                    zone_connects[c.object_name] = ZoneConnect(inlet=c)
            elif c.connection_type is NodeConnect.ZoneNode:
                if c.object_name in zone_connects:
                    zone_connects[c.object_name].node = c
                else:
                    zone_connects[c.object_name] = ZoneConnect(node=c)
            elif c.connection_type is NodeConnect.ZoneReturn:
                if c.object_name in zone_connects:
                    zone_connects[c.object_name].outlet = c
                else:
                    zone_connects[c.object_name] = ZoneConnect(outlet=c)
            elif c.connection_type is NodeConnect.Inlet:
                target = component_connects
                obj = ComponentConnect
                if c.object_type == 'OUTDOORAIR:MIXER':
                    target = oasys_connects
                elif c.object_type == 'AIRLOOPHVAC:ZONEMIXER':
                    target = zonemixer_connects
                    obj = MixerConnect
                elif c.object_type == 'AIRLOOPHVAC:ZONESPLITTER':
                    target = zonesplitter_connects
                    obj = SplitterConnect
                if c.object_name in target:
                    target[c.object_name].inlet = c
                else:
                    target[c.object_name] = obj(inlet=c)
            elif c.connection_type is NodeConnect.Outlet:
                target = component_connects
                obj = ComponentConnect
                if c.object_type == 'OUTDOORAIR:MIXER':
                    target = oasys_connects
                elif c.object_type == 'AIRLOOPHVAC:ZONEMIXER':
                    target = zonemixer_connects
                    obj = MixerConnect
                elif c.object_type == 'AIRLOOPHVAC:ZONESPLITTER':
                    target = zonesplitter_connects
                    obj = SplitterConnect
                if c.object_name in target:
                    target[c.object_name].outlet = c
                else:
                    target[c.object_name] = obj(outlet=c)
        # Check that it has all worked oit
        for el in list(zone_connects.values()) + list(component_connects.values()) + list(oasys_connects.values()):
            if not el.valid():
                raise BranchNodeDetailsFailure('Failed to correctly parse BND file.')
            
        regular_node_list = []
        link_list = []
        regular_elements = {
            "AirflowNetwork:Distribution:Component:TerminalUnit": {},
            "AirflowNetwork:Distribution:Component:HeatExchanger": {},
            "AirflowNetwork:Distribution:Component:Coil": {},
            "AirflowNetwork:Distribution:Component:Fan": {},
            "AirflowNetwork:Distribution:Component:Duct": {}
        }
        # Handle the regular compoents
        for name, comp in component_connects.items():
            assert comp.inlet.object_type == comp.outlet.object_type
            try:
                obj = equivalent_lookup[comp.inlet.object_type]
            except KeyError:
                raise UnsupportedObject('Encountered unsupported object "%s"' % comp.inlet.object_type)
            print(name.title()+' AFN Link')
            element_name = name.title() + ' AFN Equivalent'
            regular_elements[obj][element_name] = equivalent_handler[obj](object_name=name, object_type=comp.inlet.object_type)
            regular_node_list.append(comp.inlet.node.name)
            regular_node_list.append(comp.outlet.node.name)
            link_list.append(DistributionLinkage(name=name, component_name=element_name,
                                                node_1_name=comp.inlet.node.name.title() + ' AFN Node',
                                                node_2_name=comp.outlet.node.name.title() + ' AFN Node'))

        # Handle splitters
        splitter_nodes = {} # There should be one of these per air loop, I hope
        splitter_ducts = {}
        splitter_links = []
        for name, comp in zonesplitter_connects.items():
            assert comp.inlet.object_type == comp.outlet.object_type
            # Figure out which air loop we are on
            try:
                path_component = bnd.supply_air_path_components[name]
            except KeyError:
                raise BranchNodeDetailsFailure('Failed to find splitter path component')
            print(path_component.airloophvac_name)
            if path_component.airloophvac_name in splitter_nodes:
                raise BranchNodeDetailsFailure('Encountered mulitiple splitters')
            splitter_node_name = name.title() + ' AFN Splitter Node'
            splitter_nodes[path_component.airloophvac_name] = ObjectNode(name=splitter_node_name,
                                                                        type="AirLoopHVAC:ZoneSplitter")
            element_name = element_name = name.title() + ' AFN Mixer Duct'
            splitter_ducts[element_name] = default_duct()
            splitter_links.append(DistributionLinkage(name=name.title() + ' AFN Splitter Link', 
                                                    component_name=element_name,
                                                    node_1_name=comp.inlet.node.name.title() + ' AFN Node', 
                                                    node_2_name=splitter_node_name))
            for outlet in comp.outlets:
                element_name = outlet.node.name.title() + ' AFN Splitter Duct'
                splitter_ducts[element_name] = default_duct()
                splitter_links.append(DistributionLinkage(name = outlet.node.name.title() + ' AFN Splitter Link',
                                                        component_name=element_name,
                                                        node_1_name=splitter_node_name,
                                                        node_2_name=outlet.node.name.title() + ' AFN Splitter Node'))

        # Handle mixers
        mixer_nodes = {} # There should be one of these per air loop, I hope
        mixer_ducts = {}
        mixer_links = []
        for name, comp in zonemixer_connects.items():
            assert comp.inlet.object_type == comp.outlet.object_type
            # Figure out which air loop we are on
            try:
                path_component = bnd.return_air_path_components[name]
            except KeyError:
                raise BranchNodeDetailsFailure('Failed to find mixer path component')
            print(path_component.airloophvac_name)
            if path_component.airloophvac_name in mixer_nodes:
                raise BranchNodeDetailsFailure('Encountered mulitiple mixers')
            mixer_node_name = name.title() + ' AFN Mixer Node'
            mixer_nodes[path_component.airloophvac_name] = ObjectNode(name=mixer_node_name,
                                                                    type="AirLoopHVAC:ZoneMixer")
            for inlet in comp.inlets:
                element_name = inlet.node.name.title() + ' AFN Mixer Duct'
                mixer_ducts[element_name] = default_duct()
                mixer_links.append(DistributionLinkage(name=inlet.node.name.title() + ' AFN Mixer Link', 
                                                    component_name=element_name,
                                                    node_1_name=inlet.node.name.title() + ' AFN Node',
                                                    node_2_name=mixer_node_name))
            element_name = name.title() + ' AFN Mixer Duct'
            mixer_ducts[element_name] = default_duct()
            mixer_links.append(DistributionLinkage(name=name.title() + ' AFN Mixer Link',
                                                component_name=element_name, 
                                                node_1_name=mixer_node_name,
                                                node_2_name=comp.outlet.node.name.title() + ' AFN Node'))

        # Handle the zone connections
        zone_links = []
        zone_ducts = {}
        zones = []
        for name, con in zone_connects.items():
            # name should be the zone name here
            assert con.inlet.object_type == con.outlet.object_type
            print(con.inlet.object_type, con.inlet.object_name, name)
            zones.append(name)
            element_name = name.title() + ' AFN Supply Duct'
            zone_ducts[element_name] = default_duct()
            zone_links.append(DistributionLinkage(name=name.title() + ' AFN Supply Link', 
                                                component_name=element_name,
                                                node_1_name=con.inlet.node.name.title() + ' AFN Node', 
                                                node_2_name=name))
            element_name = name.title() + ' AFN Return Duct'
            zone_ducts[element_name] = default_duct()
            zone_links.append(DistributionLinkage(name=name.title() + ' AFN Return Link', 
                                                component_name=element_name,
                                                node_1_name=name,
                                                node_2_name=con.outlet.node.name.title() + ' AFN Node'))

        # Handle OA systems
        oa_links = []
        oa_nodes = []
        oa_ducts = {}
        for name, con in oasys_connects.items():
            # Create a system node
            system_node_name = name.title() + ' AFN OA System Node'
            oa_nodes.append(ObjectNode(system_node_name, 'AirLoopHVAC:OutdoorAirSystem'))
            # Create the inlet link
            element_name = name.title() + ' AFN OA Inlet Duct'
            link_name =  name.title() + ' AFN OA Inlet'
            oa_ducts[element_name] = default_duct()
            oa_links.append(DistributionLinkage(name=link_name, component_name=element_name,
                                                node_1_name=con.inlet.node.name, node_2_name=system_node_name))
            # Create the outlet link
            element_name = name.title() + ' AFN OA Outlet Duct'
            link_name =  name.title() + ' AFN OA Outlet'
            oa_ducts[element_name] = default_duct()
            oa_links.append(DistributionLinkage(name=link_name, component_name=element_name,
                                                node_1_name=system_node_name, node_2_name=con.outlet.node.name))

        regular_node_list = list(set(regular_node_list))
        regular_node_list = [RegularNode(el.title() + ' AFN Node', el) for el in regular_node_list]

        # Add objects to the model, nodes first
        if 'AirflowNetwork:Distribution:Node' not in self.model:
            self.model['AirflowNetwork:Distribution:Node'] = {}
        for el in regular_node_list + list(splitter_nodes.values()) + list(mixer_nodes.values()) + oa_nodes:
            self.model['AirflowNetwork:Distribution:Node'][el.name] = el.to_json()

        # Now add the new elements
        regular_elements['AirflowNetwork:Distribution:Component:Duct'] = {**regular_elements['AirflowNetwork:Distribution:Component:Duct'],
                                                                          **splitter_ducts, **mixer_ducts, **zone_ducts, **oa_ducts}
        for k, v in regular_elements.items():
            if v:
                if k in self.model:
                    self.model[k] = {**self.model[k], **v}
                else:
                    self.model[k] = v
    
        # Now for the links
        if 'AirflowNetwork:Distribution:Linkage' not in self.model:
            self.model['AirflowNetwork:Distribution:Linkage'] = {}
        for el in link_list + splitter_links + mixer_links + zone_links + oa_links:
            self.model['AirflowNetwork:Distribution:Linkage'][el.name] = el.to_json()
        # zones

def build_network(model, quiet:bool=False, delete_objects:bool=False, strip:bool=False,
                  window_filters=None, door_filters=None, no_openings:bool=False, no_windows:bool=False,
                  no_doors:bool=False, no_envelope:bool=False, aggregate_leakage:bool=False, 
                  bnd:BranchNodeDetails|None=None):

    global start_message
    global message
    global complete_message

    if quiet:
        start_message = silence
        message = silence
        complete_message = silence

    if no_openings:
        no_windows = True
        no_doors = True

    if window_filters is None:
        window_filters = []

    if door_filters is None:
        door_filters = []

    builder = NetworkBuilder(model, verbose=not quiet, model_envelope=not no_envelope,
                             model_windows=not no_windows, window_patterns=window_filters,
                             model_doors=not no_doors, door_patterns=door_filters,
                             aggregate=aggregate_leakage, no_openings=no_openings)

    builder.process_surfaces()
    builder.create_network()

    if bnd is not None:
        builder.build_distribution(bnd)

    message(builder.surface_stats())
    return model

