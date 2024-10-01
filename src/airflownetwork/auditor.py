# SPDX-FileCopyrightText: 2022-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
#

import json
import uuid
from .tables import all_surfaces

class BadModel(Exception):
    pass

class BaseAuditor:
    def __init__(self, model):
        self.model = model  # The model
        self.json = {}  # JSON output dictionary

    def audit(self, **kwargs):
        return True

    def add_message(self, mesg):
        if 'messages' in self.json:
            self.json['messages'].append(mesg)
        else:
            self.json['messages'] = [mesg]

def connectedness(dictionary, start):
    connected_to = set()
    current_list = dictionary.pop(start)
    for name in current_list:
        if name in dictionary:
            connected_to.update(connectedness(dictionary, name))
            connected_to.add(name)
    return connected_to

def load_epjson(file):
    with open(file, 'r') as fp:
        model = json.load(fp)
    return model

class Auditor(BaseAuditor):
    def __init__(self, model, distribution=False):
        super().__init__(model)
        self.internal_nodes = {}
        self.multizone_nodes = {}
        self.external_nodes = {}
        self.intrazone_nodes = {}
        self.intrazone_links = {}
        self.distribution_nodes = {}
        self.distribution_links = {}
        self.surfs = {}
        self.wpcs = {}
        self.refconds = {}
        self.afes = {}
        self.relative_geometry = False
        self.vertex_ccw = True
        self.distribution = distribution
        # Figure out what is what
        if 'GlobalGeometryRules' in self.model:
            obj = next(iter(self.model['GlobalGeometryRules'].values()))
            if 'coordinate_system' in obj:
                if obj['coordinate_system'] == 'Relative':
                    self.relative_geometry = True
            if 'vertex_entry_direction' == 'ClockWise':
                self.vertex_ccw = False
        if self.__extract():
            if self.__connect_multizone():
                if self.distribution:
                    self.__connect_distribution()

    def __extract(self):
        lookup = {
            'AirflowNetwork:MultiZone:Zone': self.multizone_nodes,
            'AirflowNetwork:MultiZone:Surface': self.surfs,
            'AirflowNetwork:MultiZone:ReferenceCrackConditions': self.refconds,
            'AirflowNetwork:MultiZone:Surface:Crack': self.afes,
            'AirflowNetwork:MultiZone:Surface:EffectiveLeakageArea': self.afes,
            'AirflowNetwork:MultiZone:Component:DetailedOpening': self.afes,
            'AirflowNetwork:MultiZone:Component:SimpleOpening': self.afes,
            'AirflowNetwork:MultiZone:Component:HorizontalOpening': self.afes,
            'AirflowNetwork:MultiZone:Component:ZoneExhaustFan': self.afes,
            'AirflowNetwork:MultiZone:ExternalNode': self.external_nodes,
            'OutdoorAir:Node': self.external_nodes,
            'AirflowNetwork:Distribution:Node': self.distribution_nodes,
            'AirflowNetwork:Distribution:Linkage': self.distribution_links,
            'AirflowNetwork:IntraZone:Node':self.intrazone_nodes,
            'AirflowNetwork:IntraZone:Linkage':self.intrazone_links
        }
        # Load the simcontrol object
        try:
            self.simcontrol = self.model['AirflowNetwork:SimulationControl']
        except KeyError:
            self.add_message(
                'Model does not contain an AirflowNetwork:SimulationControl object, aborting audit'
            )
            return False
        # Check for intrazone links and nodes
        #self.has_intrazone = ('AirflowNetwork:IntraZone:Node' in self.model) and (
        #    'AirflowNetwork:IntraZone:Linkage' in self.model
        #)
        # Handle the wind pressure coefficients, should maybe remove these from the model once we're done
        try:
            wpa = next(
                iter(
                    self.model[
                        'AirflowNetwork:MultiZone:WindPressureCoefficientArray'
                    ].values()
                )
            )
            keys = [el for el in wpa.keys() if el.startswith('wind_dir')]
            keys.sort()
            directions = []
            for key in keys:
                directions.append(wpa[key])

            for k, v in self.model[
                'AirflowNetwork:MultiZone:WindPressureCoefficientValues'
            ].items():
                keys = [el for el in v.keys() if el.startswith('wind_pres')]
                keys.sort()
                coeffs = []
                for key in keys:
                    coeffs.append(v[key])
                self.wpcs[k] = {
                    'wind_directions': directions,
                    'wind_pressure_coefficient_values': coeffs,
                }
        except KeyError:
            self.wpcs = {}

        # Pull out the airflow network objects
        for key in self.model.keys():
            if key in lookup:
                thedict = lookup[key]
                for k, v in self.model[key].items():
                    thedict[k.upper()] = v

        # Combine the internal nodes into a single dictionary
        self.internal_nodes = {}
        for value in self.multizone_nodes.values():
            self.internal_nodes[value['zone_name'].upper()] = value
        for key, value in self.distribution_nodes.items():
            self.internal_nodes[key.upper()] = value
        for key, value in self.intrazone_nodes.items():
            self.internal_nodes[key.upper()] = value
        return True

    def summarize_model(self, json_output=False):
        lookup = {
            '"AirflowNetwork:MultiZone:Zone"': self.multizone_nodes,
            '"AirflowNetwork:MultiZone:Surface"': self.surfs,
            '"AirflowNetwork:MultiZone:ReferenceCrackConditions"': self.refconds,
            'airflow element': self.afes,
            '"AirflowNetwork:MultiZone:ExternalNode"': self.external_nodes,
        }
        lines = []
        for key, thedict in lookup.items():
            if len(thedict) > 0:
                lines.append('Number of %s objects: %d' % (key, len(thedict)))
        return lines

    def write_dot(self, fp):
        if self.multizone_nodes == []:
            self.add_message(
                'Warning: graph output not produced because no nodes were found'
            )
            return
        if self.surfs == []:  # this isn't quite right, but good enough for now
            self.add_message(
                'Warning: graph output not produced because no linkages were found'
            )
            return
        #
        # Generate a graph
        #
        # Give nodes names for display
        count = 0
        for name, node in self.external_nodes.items():
            node['display_name'] = 'E%d' % count
            count += 1
        count = 0
        for name, node in self.multizone_nodes.items():
            node['display_name'] = 'Z%d' % count
            count += 1
        count = 0
        for name, node in self.distribution_nodes.items():
            node['display_name'] = 'D%d' % count
            count += 1
        count = 0
        for name, node in self.intrazone_nodes.items():
            node['display_name'] = 'I%d' % count
            count += 1

        fp.write('graph linkages {\n')
        for name, surf in self.surfs.items():
            fp.write(
                '%s -- %s\n'
                % (surf['nodes'][0]['display_name'], surf['nodes'][1]['display_name'])
            )
        #print(len(self.intrazone_links))
        for name, link in self.intrazone_links.items():
            fp.write(
                '%s -- %s\n'
                % (link['nodes'][0]['display_name'], link['nodes'][1]['display_name'])
            )
        if self.distribution:
            for name, link in self.distribution_links.items():
                print(link)
                fp.write(
                    '%s -- %s\n'
                    % (link['nodes'][0]['display_name'], link['nodes'][1]['display_name'])
                )
        fp.write('}\n')

    def summarize(self):
        lines = [
            'Maximum multizone links: %s(%s): %d'
            % (
                self.json['max_multizone_links']['zone'],
                self.json['max_multizone_links']['afn_zone'],
                self.json['max_multizone_links']['count'],
            ),
            ' Maximum external links: %s(%s): %d'
            % (
                self.json['max_external_links']['zone'],
                self.json['max_external_links']['afn_zone'],
                self.json['max_external_links']['count'],
            ),
        ]
        messages = self.json.get('messages', [])
        for mesg in messages:
            lines.append(mesg)
        return lines

    def __connect_distribution(self):
        for name, node in self.distribution_nodes.items():
            node['link_count'] = 0
            node['external_connections'] = 0  # not currently implemented
            node['distribution_connections'] = 0
            node['neighbors'] = {}
            node['is_distribution'] = True
        for name, link in self.distribution_links.items():
            node_names = (link['node_1_name'].upper(), link['node_2_name'].upper())
            link['nodes'] = []
            for node_name in node_names:
                link['nodes'].append(self.internal_nodes[node_name])
                self.internal_nodes[node_name]['link_count'] += 1
            # Count the numbers of connections
            self.internal_nodes[node_names[1]]['link_count'] += 1
            if self.internal_nodes[node_names[0]]['is_distribution']:
                self.internal_nodes[node_names[1]]['distribution_connections'] += 1
            if node_names[0] in self.internal_nodes[node_names[1]]['neighbors']:
                self.internal_nodes[node_names[1]]['neighbors'][node_names[0]] += 1
            else:
                self.internal_nodes[node_names[1]]['neighbors'][node_names[0]] = 1
            self.internal_nodes[node_names[0]]['link_count'] += 1
            if self.internal_nodes[node_names[1]]['is_distribution']:
                self.internal_nodes[node_names[0]]['distribution_connections'] += 1
            if node_names[1] in self.internal_nodes[node_names[0]]['neighbors']:
                self.internal_nodes[node_names[0]]['neighbors'][node_names[1]] += 1
            else:
                self.internal_nodes[node_names[0]]['neighbors'][node_names[1]] = 1

    def __connect_multizone(self):
        # Link surfaces to nodes, need to automate this better at some point
        for name, node in self.multizone_nodes.items():
            node['link_count'] = 0
            node['external_connections'] = 0
            node['distribution_connections'] = 0
            node['neighbors'] = {}
            node['is_distribution'] = False

        for name, node in self.intrazone_nodes.items():
            node['link_count'] = 0
            node['external_connections'] = 0
            node['distribution_connections'] = 0
            node['neighbors'] = {}
            node['is_distribution'] = False

        for name, node in self.external_nodes.items():
            node['link_count'] = 0
            node['neighbors'] = {}

        # heat_transfer_surface_names = [
        #    "BuildingSurface:Detailed",
        #    "FenestrationSurface:Detailed",
        # ]

        heat_transfer_surface_names = all_surfaces

        htsurfs = {}
        for name in heat_transfer_surface_names:
            if name in self.model:
                htsurfs.update(self.model[name])

        outdoor_count = 0

        # Handle the surfaces
        for name, surf in self.surfs.items():
            window = None
            try:
                htsurf = htsurfs[surf['surface_name']]
            except KeyError:
                try:
                    htsurf = htsurfs[surf['surface_name'].upper()]
                except KeyError:
                    raise BadModel(
                        'Failed to find heat transfer surface for AirflowNetwork surface "'
                        + surf['surface_name']
                        + '"'
                    )
            if 'building_surface_name' in htsurf:
                window = htsurf
                try:
                    htsurf = htsurfs[window['building_surface_name']]
                except KeyError:
                    raise BadModel(
                        'Failed to find window heat transfer surface for AirflowNetwork surface "'
                        + name
                        + '"'
                    )

            bc = htsurf['outside_boundary_condition']

            # Find the associated internal zone
            zone_name = htsurf['zone_name'].upper()
            afnzone = None
            if zone_name in self.internal_nodes: # should probably be using just the mz nodes here
                afnzone = self.internal_nodes[zone_name]
            else:
                raise BadModel(
                    'Failed to find AirflowNetwork zone for thermal zone "'
                    + zone_name
                    + '"'
                )
            
            # Figure out what the other node is
            other_node = None
            if bc == 'Outdoors':
                outdoor_count += 1
                try:
                    external_node_name = surf['external_node_name'].upper()
                except KeyError:
                    # This is probably a model using precomputed WPCs, should check that
                    external_node_name = uuid.uuid4().hex[:6].upper()
                    self.external_nodes[external_node_name] = {
                        'link_count': 0,
                        'zone_name': None,
                        'neighbors': {},
                    }
                    surf['external_node_name'] = external_node_name
                try:
                    external_node = self.external_nodes[external_node_name]
                except KeyError:
                    # Check here for the special names
                    if external_node_name in ['NFACADE', 'SFACADE', 'EFACADE', 'WFACADE']:
                        external_node = {
                            'link_count': 0,
                            'zone_name': None,
                            'neighbors': {},
                        }
                        self.external_nodes[external_node_name] = external_node
                    else:
                        raise BadModel(
                            'Failed to find external node "'
                            + external_node_name
                            + '" for AirflowNetwork surface "'
                            + name
                            + '"'
                        )
                external_node['link_count'] += 1
                
                afnzone['link_count'] += 1
                afnzone['external_connections'] += 1
                if surf['external_node_name'] in afnzone['neighbors']:
                    afnzone['neighbors'][surf['external_node_name']] += 1
                else:
                    afnzone['neighbors'][surf['external_node_name']] = 1
                if zone_name in external_node['neighbors']:
                    external_node['neighbors'][zone_name] += 1
                else:
                    external_node['neighbors'][zone_name] = 1

                other_node = external_node
            elif bc == 'Surface':
                afnzone['link_count'] += 1

                adjhtsurf = htsurfs[htsurf['outside_boundary_condition_object']]
                adj_zone_name = adjhtsurf['zone_name'].upper()
                if adj_zone_name in self.internal_nodes: # Still probably only need to do use the mz nodes
                    other_node = self.internal_nodes[adj_zone_name]
                else:
                    raise BadModel(
                        'Failed to find AirflowNetwork zone for adjacent thermal zone "'
                        + adj_zone_name
                        + '"'
                    )
                other_node['link_count'] += 1
                if adj_zone_name in afnzone['neighbors']:
                    afnzone['neighbors'][adj_zone_name] += 1
                else:
                    afnzone['neighbors'][adj_zone_name] = 1
                if zone_name in other_node['neighbors']:
                    other_node['neighbors'][zone_name] += 1
                else:
                    other_node['neighbors'][zone_name] = 1
            elif bc == 'Zone':
                afnzone['link_count'] += 1
                adj_zone_name = htsurf['outside_boundary_condition_object'].upper()
                if adj_zone_name in self.internal_nodes: # Still probably only need to do use the mz nodes
                    other_node = self.internal_nodes[adj_zone_name]
                else:
                    raise BadModel(
                        'Failed to find AirflowNetwork zone for adjacent thermal zone "'
                        + adj_zone_name
                        + '"'
                    )
                other_node['link_count'] += 1
                if adj_zone_name in afnzone['neighbors']:
                    afnzone['neighbors'][adj_zone_name] += 1
                else:
                    afnzone['neighbors'][adj_zone_name] = 1
                if zone_name in other_node['neighbors']:
                    other_node['neighbors'][zone_name] += 1
                else:
                    other_node['neighbors'][zone_name] = 1

            if other_node is None:
                raise BadModel('Failed to resolve linked nodes for AirflowNetwork surface "' + name + '"')

            surf['nodes'] = [afnzone, other_node]
        
        # Handle the intrazone links
        for name, link in self.intrazone_links.items():
            node_names = (link['node_1_name'].upper(), link['node_2_name'].upper())
            link['nodes'] = []
            for node_name in node_names:
                link['nodes'].append(self.internal_nodes[node_name])
                self.internal_nodes[node_name]['link_count'] += 1
            # Count the numbers of connections
            self.internal_nodes[node_names[1]]['link_count'] += 1
            if node_names[0] in self.internal_nodes[node_names[1]]['neighbors']:
                self.internal_nodes[node_names[1]]['neighbors'][node_names[0]] += 1
            else:
                self.internal_nodes[node_names[1]]['neighbors'][node_names[0]] = 1
            self.internal_nodes[node_names[0]]['link_count'] += 1
            if node_names[1] in self.internal_nodes[node_names[0]]['neighbors']:
                self.internal_nodes[node_names[0]]['neighbors'][node_names[1]] += 1
            else:
                self.internal_nodes[node_names[0]]['neighbors'][node_names[1]] = 1
        return True

    def get_neighbors(self, no_distribution=True):
        # The argument no_distribution is different than the member var so that just the multizone
        # neighbors can be collected even if there is distribution.
        dictionary = {}
        # Need to handle this all better, this is required to handle the zone/node naming issue
        node_dict = self.multizone_nodes
        rename = lambda key, value: value['zone_name']
        if not no_distribution:
            node_dict = self.internal_nodes
            rename = lambda key, value: key
        for node_name, node in node_dict.items():
            dictionary[rename(node_name, node).upper()] = [
                name.upper() for name in node['neighbors'].keys()
            ]
        for node_name, node in self.external_nodes.items():
            dictionary[node_name] = [name.upper() for name in node['neighbors'].keys()]
        return dictionary

    def audit(self, **kwargs):
        if self.multizone_nodes == {} or self.external_nodes == {} or self.surfs == {}:
            # This is not a super great way to get this done, should reconsider
            if self.__extract():
                if self.__connect_multizone():
                    if self.distribution:
                        self.__connect_distribution()
        #
        # Now we've got the links worked out, so proceed to looking at what was there
        #
        node_dict = self.multizone_nodes
        if self.distribution:
            node_dict = self.internal_nodes
        link_histogram = {}
        external_link_histogram = {}
        distribution_link_histogram = {}
        max_link_node_name = None
        max_links = 0
        max_external_link_node_name = None
        max_external_links = 0
        for name, node in node_dict.items():
            if node['link_count'] > max_links:
                max_link_node_name = name
                max_links = node['link_count']
            if node['link_count'] in link_histogram:
                link_histogram[node['link_count']] += 1
            else:
                link_histogram[node['link_count']] = 1
            if node['external_connections'] > max_external_links:
                max_external_link_node_name = name
                max_external_links = node['external_connections']
            if node['external_connections'] in external_link_histogram:
                external_link_histogram[node['external_connections']] += 1
            else:
                external_link_histogram[node['external_connections']] = 1
            if node['distribution_connections'] in distribution_link_histogram:
                distribution_link_histogram[node['distribution_connections']] += 1
            else:
                distribution_link_histogram[node['distribution_connections']] = 1

        #
        # For a simple brick zone, 6 multizone links would connect it to all neighbors.
        # In real models, it's unlikely that 6 is a good number to test against, so let's
        # hardcode this as roughly quadruple that, or 25
        #
        large_links = 0
        too_many_links = 0
        way_too_many_links = 0
        for k, v in link_histogram.items():
            if k >= 25:
                large_links += v
            if k >= 50:
                too_many_links += v
            if k >= 100:
                way_too_many_links += v

        # Do the same thing for external connections, but using 2 as the ideal, quadruple that
        # would be ~8
        large_external_links = 0
        too_many_external_links = 0
        way_too_many_external_links = 0
        for k, v in external_link_histogram.items():
            if k >= 8:
                large_external_links += v
            if k >= 16:
                too_many_external_links += v
            if k >= 32:
                way_too_many_external_links += v

        #
        # Machine-readable output of the link counts
        #
        self.json['distribution_link_histogram'] = distribution_link_histogram
        self.json['multizone_link_histogram'] = link_histogram
        self.json['max_multizone_links'] = {
            'zone': node_dict[max_link_node_name]['zone_name'],
            'afn_zone': max_link_node_name,
            'count': max_links,
        }
        self.json['external_link_histogram'] = external_link_histogram
        self.json['max_external_links'] = {
            'zone': node_dict[max_external_link_node_name]['zone_name'],
            'afn_zone': max_external_link_node_name,
            'count': max_external_links,
        }
        if large_links > 0:
            mesg = '%d zone(s) with greater than 25 links' % large_links
            if too_many_links > 0:
                mesg += ', %d with greater than 50 links' % too_many_links
                if way_too_many_links > 0:
                    mesg += ', %d with greater than 100 links' % way_too_many_links
                    mesg += ', model performance may suffer'
            self.add_message(mesg)
        if large_external_links > 0:
            mesg = (
                '%d zone(s) with greater than 8 external links' % large_external_links
            )
            if too_many_external_links > 0:
                mesg += (
                    ', %d with greater than 16 external links' % too_many_external_links
                )
                if way_too_many_external_links > 0:
                    mesg += (
                        ', %d with greater than 32 external links'
                        % way_too_many_external_links
                    )
                    mesg += ', model performance may suffer'
            self.add_message(mesg)

        #
        # Check that distribution nodes are all pointing to different components
        #
        if self.distribution:
            duplicates = []
            used_components = {}
            for name, node in self.distribution_nodes.items():
                if 'component_name_or_node_name' in node:
                    if node['component_name_or_node_name'] in used_components:
                        duplicates.append(
                            (name, used_components[node['component_name_or_node_name']])
                        )
                    else:
                        used_components[node['component_name_or_node_name']] = name
            self.json['duplicate distribution nodes'] = False
            if duplicates:
                self.json['duplicate distribution nodes'] = True

        #
        # Check connectedness of the model, first multizone only
        #
        neighbors = self.get_neighbors()
        starter = next(iter(neighbors.keys()))
        connectedness(neighbors, starter)
        # Check that the starter node is connected to the rest of the nodes,
        # which will be true if the neighbors dictionary is empty
        self.json['multizone connected'] = True
        if neighbors:
            self.json['multizone connected'] = False
            self.add_message('Multizone network is not fully connected')

        #
        # Check distribution if needed
        #
        self.json['connected'] = self.json['multizone connected']
        # print(self.internal_nodes.keys())
        if self.distribution:
            neighbors = self.get_neighbors(no_distribution=False)
            starter = next(iter(neighbors.keys()))
            connectedness(neighbors, starter)
            # Check that the starter node is connected to the rest of the nodes,
            # which will be true if the neighbors dictionary is empty
            self.json['connected'] = True
            if neighbors:
                self.json['connected'] = False
                self.add_message(
                    'Network (multizone + distribution) is not fully connected'
                )
