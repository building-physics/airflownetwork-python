# SPDX-FileCopyrightText: 2022-present Oak Ridge National Laboratory, managed by UT-Battelle
#
# SPDX-License-Identifier: BSD-3-Clause
#
import enum
import json
import os
import ast
import copy

class IncompleteFile(Exception):
    pass

class BadFormat(Exception):
    pass

class ElementNotFound(Exception):
    pass

class ProgramVersion:
    def __init__(self, name, version, timestamp):
        self.name = name
        self.version = version
        self.timestamp = timestamp

class Node:
    def __init__(self, number, name, fluid, refs, used=False,
                 eliminated=False):
        self.number = number
        self.name = name
        self.fluid = fluid
        self.refs = refs
        self.used = used
        self.merged = eliminated

class BranchList:
    def __init__(self, count, name, loop_name, loop_type, branches):
        self.count = count
        self.name = name
        self.loop_name = loop_name
        self.loop_type = loop_type
        self.branches = branches

class Branch:
    def __init__(self, count, name, loop_name, loop_type, inlet_node,
                 outlet_node):
        self.count = count
        self.name = name
        self.loop_name = loop_name
        self.loop_type = loop_type
        self.inlet_id = inlet_node
        self.outlet_id = outlet_node
        self.component_set=[]

class AirPaths:  #This class can be used for both Supply air paths and regurn air paths.
    def __init__(self,count,airpath_name,airloophvac_name):
        self.count=count
        self.airpath_name=airpath_name
        self.airloophvac_name=airloophvac_name

class AirPathComponent: #This class can be used for both Supply air path components and return air path components
    def __init__(self,count,component_type,component_name,airloophvac_name,is_supply=False):
        self.count=count
        self.component_type=component_type
        self.component_name=component_name
        self.airloophvac_name=airloophvac_name
        self.is_supply=is_supply

class AirPathNodes:#This class can be used for both Supply air path component nodes and return air path component nodes
    def __init__(self,node_type,node_count,node_name,airloophvac_name,is_supply=False):
        self.node_type=node_type
        self.node_count=node_count
        self.node_name=node_name
        self.airloophvac_name=airloophvac_name
        self.is_supply=is_supply
        
class ComponentSet:
    def __init__(self,count,parent_type,parent_name,component_type,component_name,inlet_id,outlet_id,description):
        self.count=count
        self.parent_type=parent_type
        self.parent_name=parent_name
        self.component_type=component_type
        self.component_name=component_name
        self.inlet_id=inlet_id
        self.outlet_id=outlet_id
        self.description=description

class Loop: #This class can be used for both plant loop and condensor loop
    def __init__(self,loop_name,loop_type,inlet_node_name,outlet_node_name,branch_list,connector_list):
        self.loop_name=loop_name
        self.loop_type=loop_type
        self.inlet_node_name=inlet_node_name
        self.outlet_node_name=outlet_node_name
        self.branch_list=branch_list
        self.connector_list=connector_list
        self.demand_loop=[]
        self.supply_loop=[]

class LoopConnector:
    def __init__(self,connector_type,connector_name,loop_name,loop_type,number_inlet_outlet):
        self.connector_type=connector_type
        self.connector_name=connector_name
        self.loop_name=loop_name
        self.loop_type=loop_type
        self.number_inlet_outlet=number_inlet_outlet

class LoopConnectorBranches:
    def __init__(self,connector_node_count,connector_type,connector_name,inlet_branch,outlet_branch,loop_name,loop_type):
        self.connector_node_count=connector_node_count
        self.connector_type=connector_type
        self.connector_name=connector_name
        self.inlet_branch=inlet_branch
        self.outlet_branch=outlet_branch
        self.loop_name=loop_name
        self.loop_type=loop_type
        
class LoopConnectorNodes:
    def __init__(self,connector_node_count,connector_type,connector_name,inlet_branch,outlet_branch,loop_name,loop_type):
        self.connector_node_count=connector_node_count
        self.connector_type=connector_type
        self.connector_name=connector_name
        self.inlet_branch=inlet_branch
        self.outlet_branch=outlet_branch
        self.loop_name=loop_name
        self.loop_type=loop_type

class LoopConnection: #This applicees to both Loop supply connection and loop return connection
    def __init__(self, loop_name,outlet_node, inlet_node, is_plant=False, is_supply=False):
        # Items from the BND file
        self.plant_loop_name = loop_name
        self.outlet_node = outlet_node
        self.inlet_node = inlet_node
        # Others
        self.is_plant = is_plant
        self.is_supply = is_supply       

class ControlledZoneInlet:
    def __init__(self, number, controlled_zone, supply_air_inlet_node, sd_sys_inlet_node,
                 dd_sys_heating_inlet_node):
        self.number = number
        self.controlled_zone_name = controlled_zone
        self.supply_air_inlet_node = supply_air_inlet_node
        self.sd_sys_inlet_node = sd_sys_inlet_node
        self.dd_sys_heating_inlet_node = dd_sys_heating_inlet_node

class ControlledZoneExhaust:
    def __init__(self, number, controlled_zone, exhaust_air_node):
        self.number = number
        self.controlled_zone_name = controlled_zone
        self.exhaust_air_node_name = exhaust_air_node
        
class ControlledZoneReturn:
    def __init__(self, number, controlled_zone, exhaust_air_node):
        self.number = number
        self.controlled_zone_name = controlled_zone
        self.exhaust_air_node_name = exhaust_air_node

class AirLoopHVAC:
    def __init__(self, name, num_return_nodes, num_supply_nodes, num_zones_cooled, num_zones_heated, outdoor_air_used):
        self.name = name
        self.num_return_nodes=num_return_nodes
        self.num_supply_nodes=num_supply_nodes
        self.num_zones_cooled=num_zones_cooled
        self.num_zones_heated=num_zones_heated
        self.outdoor_air_used=outdoor_air_used.lower() == 'yes'
        self.branch=[]
        self.supply_connections=[]
        self.return_connections=[]
        self.cooled_zone_info=[]
        self.heated_zone_info=[]
        self.demand_loop=[]
        self.supply_loop=[]

class AirLoopConnections: # This represents the connection for both airloop supply and return based on the toggle
    def __init__(self, count, airloophvac, zn_eqp_node, airloop_node, is_supply=False):
        # Items from the BND file
        self.number = count
        self.airloophvac = airloophvac
        self.zn_eqp_node = zn_eqp_node
        self.airloop_node = airloop_node
        # Others
        self.is_supply = is_supply

class ConditionedZoneInfo: #This is for both CooledZoneInfo and HeatedZoneInfo
    def __init__(self,zone_count,zone_name,inlet_node_number,inlet_node_name,airloophvac,is_cooled=True):
        self.zone_count=zone_count
        self.zone_name=zone_name
        self.inlet_node_number=inlet_node_number
        self.inlet_node_name=inlet_node_name
        self.airloophvac=airloophvac
        self.is_cooled=is_cooled

class NodeConnection: #This represents both parent node connections and non-parent node connections
    def __init__(self, node, object_type, object_name, connection_type,
                 fluid_stream, is_parent=False):
        # Items from the BND file
        self.node = node
        self.object_type = object_type
        self.object_name = object_name
        if connection_type in NodeConnect:
            self.connection_type = connection_type
        else:
            self.connection_type = NodeConnect.from_upper(connection_type.upper())
        self.fluid_stream = fluid_stream
        # Other items
        self.is_parent = is_parent 
       
class ZoneEquipmentComponent:
    def __init__(self,component_count,component_type,component_name,zone_name,heating_priority,cooling_priority):
        self.component_count=component_count
        self.component_type=component_type
        self.component_name=component_name
        self.zone_name=zone_name
        self.heating_priority=heating_priority
        self.cooling_priority=cooling_priority

class ContainsEnumMeta(enum.EnumMeta): 
    def __contains__(cls, value): 
        #return value in [v.value for v in cls.__members__.values()]
        try:
            cls(value)
        except ValueError:
            return False
        else:
            return True

class NodeConnect(enum.Enum, metaclass=ContainsEnumMeta):
    Inlet = 1
    Outlet = 2
    Internal = 3
    ZoneNode = 4
    Sensor = 5
    Actuator = 6
    OutsideAir = 7
    ReliefAir = 8
    ZoneInlet = 9
    ZoneReturn = 10
    ZoneExhaust = 11
    Setpoint = 12
    Electric = 13  # Unused?
    OutsideAirReference = 14 # Unused?

    def from_upper(name):
        try:
            return {'INLET': NodeConnect.Inlet, 'OUTLET': NodeConnect.Outlet,
                    'INTERNAL': NodeConnect.Internal, 'ZONENODE': NodeConnect.ZoneNode,
                    'SENSOR': NodeConnect.Sensor, 'ACTUATOR': NodeConnect.Actuator,
                    'OUTDOORAIR': NodeConnect.OutsideAir, 'RELIEFAIR': NodeConnect.ReliefAir,
                    'ZONEINLET': NodeConnect.ZoneInlet, 'ZONERETURN': NodeConnect.ZoneReturn,
                    'ZONEEXHAUST': NodeConnect.ZoneExhaust, 'SETPOINT': NodeConnect.Setpoint}[name]
        except KeyError:
            return None

def read_nodes(fp, n, line_number):
    count = 0
    nodes = []
    for line in fp:
        line = line.strip()
        line_number += 1
        if line.startswith('!'):
            continue
        count += 1
        data = line.split(',')
        if len(data) != 5:
            raise BadFormat('Too many elements in node entry at line %d' % line_number)
        try:
            data[1] = int(data[1])
        except ValueError:
            raise BadFormat('Bad node number field "%s" at line %d' % (data[1], line_number))
        try:
            data[4] = int(data[4])
        except ValueError:
            raise BadFormat('Bad node reference count field "%s" at line %d' % (data[4], line_number))
        nodes.append(Node(*data[1:]))
        if count >= n:
            break
    else:
        raise IncompleteFile('File incomplete reading nodes at line %d' % line_number)
    return nodes, line_number

def read_branches(fp, n, line_number, nodes):
    count = 0
    branches = []
    for line in fp:
        line = line.strip()
        line_number += 1
        if line.startswith('!'):
            continue
        count += 1
        data = line.split(',')
        if len(data) != 7:
            raise BadFormat('Too many elements in branch entry at line %d' % line_number)
        try:
            count = int(data[1])
        except ValueError:
            raise BadFormat('Bad branch count field "%s" at line %d' % (data[1], line_number))
        try:
            outlet_node = nodes[data[5]]
        except KeyError:
            raise BadFormat('Bad outlet node name "%s" at line %d' % (data[5], line_number))
        try:
            inlet_node = nodes[data[6]]
        except KeyError:
            raise BadFormat('Bad inlet node name "%s" at line %d' % (data[6], line_number))
        branches.append(Branch(count, data[2], data[3], data[4], inlet_node, outlet_node))
        if count >= n:
            break
    else:
        raise IncompleteFile('File incomplete reading nodes at line %d' % line_number)
    return branches, line_number

def reverse(list_of_lists):
    list_of_lists.reverse()
    for element in list_of_lists:
        if isinstance(element,list):
            element=reverse(element)
    return list_of_lists  

def check_sub(lst,string):
    return any( ele in string for ele in lst)

def read_branch_lists(fp, n, line_number, nodes):
    count = 0
    branch_lists = []
    for line in fp:
        line = line.strip()
        line_number += 1
        if line.startswith('!'):
            continue
        count += 1
        data = line.split(',')
        if len(data) != 6:
            raise BadFormat('Too many elements in branch list entry at line %d' % line_number)
        try:
            number = int(data[1])
        except ValueError:
            raise BadFormat('Bad branch list count field "%s" at line %d' % (data[1], line_number))
        try:
            n_branches = int(data[5])
        except ValueError:
            raise BadFormat('Bad number of branches field "%s" at line %d' % (data[5], line_number))
        branches, line_number = read_branches(fp, n_branches, line_number, nodes)
        branch_lists.append(BranchList(number, data[2], data[3], data[4], branches))
        if count >= n:
            break
    else:
        raise IncompleteFile('File incomplete reading branch lists at line %d' % line_number)
    return nodes, line_number

def skip_lines(fp, n, line_number, mesg):
    count = 0
    for line in fp:
        line = line.strip()
        line_number += 1
        if line.startswith('!'):
            continue
        count += 1
        if count >= n:
            break
    else:
        raise IncompleteFile('File incomplete %s at line %d' % (mesg, line_number))
    return line_number

def connection_link(loop):
    connection={}
    
    """This is to group the inlet and outlet branch without using pandas"""
    #Group by inlet branch
    for branch in loop: 
        if branch.inlet_branch not in connection.keys():
            connection[branch.inlet_branch]=[branch.outlet_branch]
        else:
            connection[branch.inlet_branch].append(branch.outlet_branch)
    
    #Keet the intlet branch grouping in a list
    connection_list=[]
    for keys,values in connection.items():        
        connection_list.append([keys,values])
        
    #Group the list of by outlet branch 
    connection_aggregate={}
    for items in connection_list:
        if str(items[1]) not in connection_aggregate.keys():
            connection_aggregate[str(items[1])]=[items[0]]
        else:
            connection_aggregate[str(items[1])].append(items[0])
    connection_aggregated={str(y):str(x) for x,y in connection_aggregate.items()}
    
    ##Convert the dictionary of grouped items to sorted list (equivalent to linked list)
    head=[]        
    for keys_1st in connection_aggregated.keys():
        isvalue=0
        for keys_2nd in connection_aggregated.keys():
            if keys_1st in connection_aggregated[keys_2nd]:
                isvalue=isvalue+1
        if isvalue==0:
            head.append(keys_1st)
            
    connection_sorted_list=[head[0]]   
    while connection_sorted_list[-1] in connection_aggregated.keys():
       connection_sorted_list.append(connection_aggregated[connection_sorted_list[-1]]) 
    #change the element of the list to list from string   
    connection_sorted_list_strtolist=[ast.literal_eval(ele) for ele in connection_sorted_list]
    return connection_sorted_list_strtolist   

class BranchNodeDetails:
    def __init__(self, merge_aliased_nodes=False):
        self.merge_nodes=False
        self.merge_aliased_nodes = merge_aliased_nodes 
        self.airloops = {}
        self.airloop_connections = []
        self.branches=[] #This is to store branch lists
        self.component_sets=[]
        self.controlled_zone_inlets = []
        self.controlled_zone_exhausts = []
        self.controlled_zone_returns=[]
        self.line_number = 0
        self.lines=[]
        self.loop_connections = []
        self.loop_connecter=[]
        self.loop_connecter_branches=[]
        self.loop_connecter_nodes=[]
        self.nodes = []
        self.node_lookup = {}
        self.node_connections = []
        self.unexpected = []
        self.cooled_zone_info=[]
        self.heated_zone_info=[]
        self.supply_air_path_components = {}
        self.return_air_path_components = {}
        self.supply_air_path_node=[]
        self.return_air_path_node=[]
        self.zone_equipment_component=[]
        self.plantloops=[]

    @classmethod
    def read(cls, fp, merge_aliased_nodes=False):
        bnd = cls(merge_aliased_nodes=merge_aliased_nodes)
        bnd.read_file(fp)
        bnd.get_lookuptable()
        bnd.connect_objects()
        bnd.assign_objects_to_parents()
        bnd.create_airloop_supply()
        #bnd.create_airloop_demand()
        bnd.assign_plantobjects_to_parents()
        return bnd
    # =============================================================================
    #  Read the branch and node diagram and use visitor method for each data type to assign them to differnt class defined above       
    # =============================================================================
    def read_file(self, fp):
        for line in fp:
            self.line_number += 1
            self.lines.append(line)
            line = line.strip()
            if line.startswith('!'):
                continue
            data = [el.strip() for el in line.split(',')]         
            key = self.scrub_key(data[0])

            attr = 'visit_' + key            
            visitor = getattr(self, attr) #returns the value of attribute like visit_node, etc from python using data as argument
            #except AttributeError:
            #    visitor = self.visit_default
            visitor(data)
            #print(visitor(data))
    # =============================================================================
    # Make lookup table        
    # =============================================================================
    def get_lookuptable(self):       
        # 1. Create a dictionary of node name as key and node as values   
        for node in self.nodes:
            self.node_lookup[node.name] = node
            
        # Merge nodes here if requested
        if self.merge_aliased_nodes:
            self.merged_nodes = len(self.airloop_connections) != 0
            for alc in self.airloop_connections:
                node_to_eliminate = self.node_lookup[alc.zn_eqp_node]
                node_to_use = self.node_lookup[alc.airloop_node]
                node_to_eliminate.merged = True
                self.node_lookup[alc.zn_eqp_node] = node_to_use
                node_to_use.name = node_to_use.name + '/' + node_to_eliminate.name
                
    def connect_objects(self):
        # Connect things up
        # PlantLoopSupplyConnection, PlantLoopReturnConnection, CondenserLoopSupplyConnection, CondenserLoopReturnConnection
        for obj in self.loop_connections:
            obj.outlet_node = self.node_lookup[obj.outlet_node]
            obj.inlet_node = self.node_lookup[obj.inlet_node]
        # ControlledZoneInlet
        for obj in self.controlled_zone_inlets:
            obj.supply_air_inlet_node = self.node_lookup[obj.supply_air_inlet_node]
            obj.sd_sys_inlet_node = self.node_lookup[obj.sd_sys_inlet_node]
            # This next one can be "undefined", see line 544 in HVAC-Diagram-Main.f90
            try:
                obj.dd_sys_heating_inlet_node = self.node_lookup[obj.dd_sys_heating_inlet_node]
            except KeyError:
                obj.dd_sys_heating_inlet_node = None
        # ControlledZoneExhaust
        for obj in self.controlled_zone_exhausts:
            obj.exhaust_air_node = self.node_lookup[obj.exhaust_air_node]
        # AirLoopReturnConnections, AirLoopSupplyConnections
        for obj in self.airloop_connections:
            obj.airloophvac = self.airloops[obj.airloophvac]
            obj.zn_eqp_node = self.node_lookup[obj.zn_eqp_node]
            obj.airloop_node = self.node_lookup[obj.airloop_node]
        # ParentNodeConnection, NonParentNodeConnection
        for obj in self.node_connections:
            obj.node = self.node_lookup[obj.node]
        # ComponentSets
        for obj in self.component_sets:
            obj.inlet_node = self.node_lookup[obj.inlet_id]
            obj.outlet_node = self.node_lookup[obj.outlet_id]

    def set_zone_inlets_outlets(self):
        for node_connect in self.node_connections:
            if (not node_connect.is_parent and
                node_connect.connection_type == NodeConnect.ZoneReturn):
                print(node_connect.node.name, '+', node_connect.object_name)
                for zone_inlet in self.controlled_zone_inlets:
                    if zone_inlet.controlled_zone == node_connect.object_name:
                        print('\t', zone_inlet.controlled_zone)
                        print('\t\t', zone_inlet.supply_air_inlet_node.name)
                return

    def write_dot(self, fp):
        graph = {}
        for nc in self.node_connections:
            if nc.is_parent:
                continue
            if nc.connection_type not in [NodeConnect.Inlet,
                                          NodeConnect.Outlet,
                                          NodeConnect.ZoneInlet,
                                          NodeConnect.ZoneReturn]:
                continue
            if nc.node.name in graph:
                graph[nc.node.name].append(nc.object_name)
            else:
                graph[nc.node.name] = [nc.object_name]
        fp.write('graph loops {\n')
        for k,v in graph.items():
            if len(v) != 2:
                continue
            #print(k,v)
            fp.write('    "%s" -- "%s" [label="%s"]\n' % (v[0],v[1],k))
        fp.write('}\n')

    def insert_loop_shims(self):
        # Insert loop shims
        if self.merged_nodes:
            return # Maybe should throw?
        for alc in self.airloop_connections:
            if alc.is_supply:
                the_name = alc.airloophvac.name + ' SUPPLY SHIM'
                # Supply Outlet
                self.node_connections.append(NodeConnection(alc.airloop_node,
                                                            'WHAT?',
                                                            the_name,
                                                            NodeConnect.Inlet,
                                                            1,
                                                            is_parent=False))
                # Demand Inlet
                self.node_connections.append(NodeConnection(alc.zn_eqp_node,
                                                            'WHAT?',
                                                            the_name,
                                                            NodeConnect.Outlet,
                                                            1,
                                                            is_parent=False))
            else:
                the_name = alc.airloophvac.name + ' RETURN SHIM'
                # Supply Inlet
                self.node_connections.append(NodeConnection(alc.airloop_node,
                                                            'WHAT?',
                                                            the_name,
                                                            NodeConnect.Outlet,
                                                            1,
                                                            is_parent=False))
                # Demand Outlet
                self.node_connections.append(NodeConnection(alc.zn_eqp_node,
                                                            'WHAT?',
                                                            the_name,
                                                            NodeConnect.Inlet,
                                                            1,
                                                            is_parent=False))
    # =============================================================================
    # The script below are used to visit nodes and creating respective class for different objects in branch and node diagram      
    # =============================================================================
    def scrub_key(self, key):
        new_key = key.replace(' ', '_')
        new_key = new_key.replace('-', '_')
        if new_key.startswith('#'):
            new_key = 'n_' + new_key[1:]
        return new_key

    def visit_AirLoopHVAC(self, data):
        if len(data) !=7:
            raise BadFormat('Expected 7 AirLoopHVAC fields, got %d in node entry at line %d'
                            % (len(data), self.line_number))
        self.airloops[data[1]] = AirLoopHVAC(*data[1:])
        
    def visit_default(self, data):
        if data[0] not in self.unexpected:
            self.unexpected.append(data[0])

    def visit_Program_Version(self, data):
        if len(data) != 4:
            raise BadFormat('Expected 4 program version fields, got %d in program version entry at line %d'
                            % (len(data), self.line_number))
        self.program = ProgramVersion(*data[1:])

    def visit_n_Nodes(self, data):
        pass

    def visit_Node(self, data):
        if len(data) != 5:
            raise BadFormat('Expected 5 node fields, got %d in node entry at line %d'
                            % (len(data), self.line_number))
        try:
            data[1] = int(data[1])
        except ValueError:
            raise BadFormat('Bad node number field "%s" at line %d'
                            % (data[1], self.line_number))
        try:
            data[4] = int(data[4])
        except ValueError:
            raise BadFormat('Bad node reference count field "%s" at line %d'
                            % (data[4], self.line_number))
        self.nodes.append(Node(*data[1:]))
        #self.node_lookup[data[2]] = Node(*data[1:])

    def visit_Suspicious_Node(self, data):
        pass

    def visit_n_Branch_Lists(self, data):
        pass

    def visit_Branch_List(self, data):
        pass

    def visit_Branch(self, data):
        self.branches.append(Branch(*data[1:]))
        pass

    def visit_n_Supply_Air_Paths(self, data):
        pass

    def visit_Supply_Air_Path(self, data):
        pass

    def visit_n_Components_on_Supply_Air_Path(self, data):
        pass

    def visit_Supply_Air_Path_Component(self, data):
        if len(data) != 5:
            raise BadFormat('Expected 5 supply air path component fields, got %d in supply air path component entry at line %d'
                            % (len(data), self.line_number))
        self.supply_air_path_components[data[3]] = AirPathComponent(*data[1:],is_supply=True)

    def visit_n_Outlet_Nodes_on_Supply_Air_Path_Component(self, data):
        pass

    def visit_Supply_Air_Path_Component_Nodes(self, data):
        pass

    def visit_n_Nodes_on_Supply_Air_Path(self, data):
        pass

    def visit_Supply_Air_Path_Node(self, data):
        pass

    def visit_n_Return_Air_Paths(self, data):
        pass

    def visit_Return_Air_Path(self, data):
        pass


    def visit_n_Components_on_Return_Air_Path(self, data):
        pass

    def visit_Return_Air_Path_Component(self, data):
        if len(data) != 5:
            raise BadFormat('Expected 5 return air path component fields, got %d in return air path component entry at line %d'
                            % (len(data), self.line_number))
        self.return_air_path_components[data[3]] = AirPathComponent(*data[1:],is_supply=False)

    def visit_n_Inlet_Nodes_on_Return_Air_Path_Component(self, data):
        pass

    def visit_Return_Air_Path_Component_Nodes(self, data):
        pass

    def visit_n_Nodes_on_Return_Air_Path(self, data):
        pass

    def visit_Return_Air_Path_Node(self, data):
        if len(data) != 5:
            raise BadFormat('Expected 5 supply air path node filed fields, got %d in supply air path node entry at line %d'
                            % (len(data), self.line_number))
        self.return_air_path_node.append(AirPathNodes(*data[1:],is_supply=False))

    def visit_n_Outdoor_Air_Nodes(self, data):
        pass

    def visit_Outdoor_Air_Node(self, data):
        pass

    def visit_n_Component_Sets(self, data):
        pass

    def visit_Component_Set(self, data):
        self.component_sets.append(ComponentSet(*data[1:]))

    def visit_n_Plant_Loops(self, data):
        pass

    def visit_Plant_Loop(self, data):
        if len(data) != 7:
            raise BadFormat('Expected 6 plant loop fields, got %d in plant loop return entry at line %d'
                            % (len(data), self.line_number))
        self.plantloops.append(Loop(*data[1:]))

    def visit_Plant_Loop_Connector(self, data):
        if len(data) != 6:
            raise BadFormat('Expected 6 Plant Loop connecter fields, got %d in plant loop supply entry at line %d'
                            % (len(data), self.line_number))
        self.loop_connecter.append(LoopConnector(*data[1:]))

    def visit_Plant_Loop_Connector_Branches(self, data):
        if len(data) != 8:
            raise BadFormat('Expected 8 Plant Loop connecter Branches fields, got %d in plant loop supply entry at line %d'
                            % (len(data), self.line_number))
        self.loop_connecter_branches.append(LoopConnectorBranches(*data[1:]))
      

    def visit_Plant_Loop_Connector_Nodes(self, data):
        if len(data) != 8:
            raise BadFormat('Expected 8 Plant Loop connecter Nodes fields, got %d in plant loop supply entry at line %d'
                            % (len(data), self.line_number))
        self.loop_connecter_nodes.append(LoopConnectorNodes(*data[1:]))
       

    def visit_Plant_Loop_Supply_Connection(self, data):
        if len(data) != 4:
            raise BadFormat('Expected 4 plant loop supply fields, got %d in plant loop supply entry at line %d'
                            % (len(data), self.line_number))
        self.loop_connections.append(LoopConnection(*data[1:], is_plant=True, is_supply=True))


    def visit_Plant_Loop_Return_Connection(self, data):
        if len(data) != 4:
            raise BadFormat('Expected 4 plant loop return fields, got %d in plant loop return entry at line %d'
                            % (len(data), self.line_number))
        self.loop_connections.append(LoopConnection(*data[1:], is_plant=True, is_supply=False))

    def visit_n_Condenser_Loops(self, data):
        pass

    def visit_Condenser_Loop(self, data):
        pass

    def visit_Condenser_Loop_Connector(self, data):
        pass

    def visit_Condenser_Loop_Connector_Branches(self, data):
        pass

    def visit_Condenser_Loop_Connector_Nodes(self, data):
        pass

    def visit_Condenser_Loop_Supply_Connection(self, data):
        if len(data) != 4:
            raise BadFormat('Expected 4 condenser loop supply fields, got %d in condenser loop supply entry at line %d'
                            % (len(data), self.line_number))
        self.loop_connections.append(LoopConnection(*data[1:], is_plant=False, is_supply=True))

    def visit_Condenser_Loop_Return_Connection(self, data):
        if len(data) != 4:
            raise BadFormat('Expected 4 condenser loop return fields, got %d in condenser loop return entry at line %d'
                            % (len(data), self.line_number))
        self.loop_connections.append(LoopConnection(*data[1:], is_plant=False, is_supply=False))

    def visit_n_Controlled_Zones(self, data):
        pass

    def visit_Controlled_Zone(self, data):
        pass

    def visit_Controlled_Zone_Inlet(self, data):
        if len(data) != 6:
            raise BadFormat('Expected 6 controlled zone inlet fields, got %d in controlled zone inlet entry at line %d'
                            % (len(data), self.line_number))
        try:
            data[1] = int(data[1])
        except ValueError:
            raise BadFormat('Bad controlled zone inlet number field "%s" at line %d'
                            % (data[1], self.line_number))
        self.controlled_zone_inlets.append(ControlledZoneInlet(*data[1:]))

    def visit_Controlled_Zone_Exhaust(self, data):
        if len(data) != 4:
            raise BadFormat('Expected 4 controlled zone exhaust fields, got %d in controlled zone exhaust entry at line %d'
                            % (len(data), self.line_number))
        try:
            data[1] = int(data[1])
        except ValueError:
            raise BadFormat('Bad controlled zone exhaust number field "%s" at line %d'
                            % (data[1], self.line_number))
        self.controlled_zone_exhausts.append(ControlledZoneExhaust(*data[1:]))
        
    def visit_Controlled_Zone_Return(self, data):
        if len(data) != 4:
            raise BadFormat('Expected 4 controlled zone exhaust fields, got %d in controlled zone exhaust entry at line %d'
                            % (len(data), self.line_number))
        try:
            data[1] = int(data[1])
        except ValueError:
            raise BadFormat('Bad controlled zone exhaust number field "%s" at line %d'
                            % (data[1], self.line_number))
        self.controlled_zone_returns.append(ControlledZoneReturn(*data[1:]))

    def visit_n_Zone_Equipment_Lists(self, data):
        pass

    def visit_Zone_Equipment_List(self, data):
        pass

    def visit_Zone_Equipment_Component(self, data):
        if len(data) != 7:
            raise BadFormat('Expected 6 zone_equipment_component fields, got %d in ZoneEquipmentComponent at line %d'
                            % (len(data), self.line_number))
        self.zone_equipment_component.append(ZoneEquipmentComponent(*data[1:]))

    def visit_n_AirLoopHVACs(self, data):
        pass

    def visit_AirLoop_Return_Connections(self, data):
        if len(data) != 7:
            raise BadFormat('Expected 7 airloop return connections fields, got %d in airloop connection entry at line %d'
                            % (len(data), self.line_number))
        try:
            number = int(data[1])
        except ValueError:
            raise BadFormat('Bad airloop connection number "%s" at line %d'
                            % (data[1], self.line_number))
        self.airloop_connections.append(AirLoopConnections(number, data[2],
                                                           data[4], data[6], is_supply=False))

    def visit_AirLoop_Supply_Connections(self, data):
        if len(data) != 7:
            raise BadFormat('Expected 7 airloop return connections fields, got %d in airloop connection entry at line %d'
                            % (len(data), self.line_number))
        try:
            number = int(data[1])
        except ValueError:
            raise BadFormat('Bad airloop connection number "%s" at line %d'
                            % (data[1], self.line_number))
        self.airloop_connections.append(AirLoopConnections(number, data[2],
                                                           data[4], data[6], is_supply=True))

    def visit_Cooled_Zone_Info(self, data):
        if len(data) != 6:
            raise BadFormat('Expected 6 cooled_zone_info fields, got %d in airloop connection entry at line %d'
                            % (len(data), self.line_number))
        self.cooled_zone_info.append(ConditionedZoneInfo(*data[1:],is_cooled=True))


    def visit_Heated_Zone_Info(self, data):
        if len(data) != 6:
            raise BadFormat('Expected 6 heated_zone_info fields, got %d in airloop connection entry at line %d'
                            % (len(data), self.line_number))
        self.heated_zone_info.append(ConditionedZoneInfo(*data[1:],is_cooled=False))

    def visit_Outdoor_Air_Connections(self, data):
        pass

    def visit_AirLoopHVAC_Connector(self, data):
        pass

    def visit_AirLoopHVAC_Connector_Branches(self, data):
        pass

    def visit_AirLoopHVAC_Connector_Nodes(self, data):
        pass

    def visit_n_Parent_Node_Connections(self, data):
        pass

    def visit_Parent_Node_Connection(self, data):
        if len(data) != 6:
            raise BadFormat('Expected 6 parent node connections fields, got %d in connection entry at line %d'
                            % (len(data), self.line_number))
        try:
            data[5] = int(data[5])
        except ValueError:
            raise BadFormat('Bad fluid stream field "%s" at line %d'
                            % (data[5], self.line_number))
        self.node_connections.append(NodeConnection(*data[1:], is_parent=True))

    def visit_n_Non_Parent_Node_Connections(self, data):
        pass

    def visit_Non_Parent_Node_Connection(self, data):
        if len(data) != 6:
            raise BadFormat('Expected 6 nonparent node connections fields, got %d in connection entry at line %d'
                            % (len(data), self.line_number))
        try:
            data[5] = int(data[5])
        except ValueError:
            raise BadFormat('Bad fluid stream field "%s" at line %d'
                            % (data[5], self.line_number))
        self.node_connections.append(NodeConnection(*data[1:], is_parent=False))
      
    def assign_objects_to_parents(self):
        
        for branch in self.branches:
            branch.component_set=[component for component in self.component_sets if ( component.parent_type.lower() == "branch" and component.parent_name==branch.name)]
        
        for airloop in self.airloops.values():
            """assign branch list to airloops"""
            airloop.branch=[branch for branch in self.branches if branch.loop_name == airloop.name]
            
            """ assign airloop supply connections to airloops"""
            airloop.supply_connections=[supply_connection for supply_connection  in self.airloop_connections if (supply_connection.airloophvac == airloop.name and supply_connection.is_supply==True)]
            #airloop.
            
            """assign airloop retrun connections to airloops"""
            airloop.return_connections=[supply_connection for supply_connection  in self.airloop_connections if (supply_connection.airloophvac == airloop.name and supply_connection.is_supply==False)]

            """assign cooled zone and heated zone realted to airloop connection"""
            airloop.cooled_zone_names=[Zone.zone_name for Zone in self.cooled_zone_info if Zone.airloophvac==airloop.name]
            airloop.heated_zone_names=[Zone.zone_name for Zone in self.heated_zone_info if Zone.airloophvac==airloop.name]
            
            airloop.controlled_zone_names=list(set(airloop.cooled_zone_names)|set(airloop.heated_zone_names))
            """assign controlled zones inlet and return to airloop connection"""
            airloop.controlled_zone_inlets=[node for node in self.controlled_zone_inlets if (node.controlled_zone_name in airloop.controlled_zone_names)]
            
            airloop.controlled_zone_returns=[node for node in self.controlled_zone_returns if (node.controlled_zone_name in airloop.controlled_zone_names)]
            if len(airloop.controlled_zone_returns)==0:
               airloop.controlled_zone_returns=[node for node in self.controlled_zone_exhausts if (node.controlled_zone_name in airloop.controlled_zone_names)]
            
            """assign supply air path nodes and return air path nodes """
            airloop.supply_air_path_node=[node for node in self.supply_air_path_node if node.airloophvac_name == airloop.name]
            airloop.return_air_path_node=[node for node in self.return_air_path_node if node.airloophvac_name == airloop.name]
            
    
    def component_matching(self,branch,component_list=None):
        
        if component_list is not None:
            componentlist=getattr(branch,component_list)
        else:
            componentlist=branch
        
        first_element=componentlist[0]
        branch=[{"name":first_element.inlet_id,
               "type":"node"},
              {"name":first_element.component_name,
               "type":first_element.component_type},
              {"name":first_element.outlet_id,
               "type":"node"}] #
        
        for i in range(len( componentlist)-1):
            for j in range(i+1,len(componentlist)):
                component1= componentlist[i]
                component2= componentlist[j]
                if component1 != component2:
                    if component1.inlet_id == component2.outlet_id:
                       index=branch.index({"name":component1.inlet_id,
                                         "type":"node"}) 
                       branch.insert(index,{"name":component2.component_name,
                                          "type":component2.component_type})
                       branch.insert(index,{"name":component2.inlet_id,
                                          "type":"node"})

                    elif component1.outlet_id==component2.inlet_id: 
                       index=branch.index({"name":component1.outlet_id,
                                         "type":"node"})+1 
                       branch.insert(index,{"name":component2.outlet_id,
                                          "type":"node"})
                       branch.insert(index,{"name":component2.component_name,
                                          "type":component2.component_type})
        return(branch) 

    def create_airloop_supply(self):  
        """The branch and component is used for the supply side of the loop"""
        for airloop in self.airloops.values():       
            for branch in airloop.branch:  #loop over all the brances in airloop
                loop=self.component_matching(branch,component_list="component_set")                    
                airloop.supply_loop.append({"branch":branch.name,"node_component":loop})    
    
    def create_airloop_demand(self): 
        """ Supply connections..return connections and cooled/heated zone info is used for creating supply side loop"""
        for airloop in self.airloops.values():
            """The supply air path inlet node is the first node in the supply side"""
            supply_air_path_inlet_node=[node.node_name for node in airloop.supply_air_path_node if node.node_type == "Inlet Node"]  
            
# =============================================================================
#             """The supply air path outlet node are the nodes after the splitter and before the zone components"""
#             supply_air_path_outlet_node=[node.node_name for node in airloop.supply_air_path_node if node.node_type != "Inlet Node"]
#             
#             """The return air path inlet node are   the nodes before the mixer"""
#             return_air_path_inlet_node=[node.node_name for node in airloop.return_air_path_node if node.node_type == "Inlet Node"]
# =============================================================================
            
            """The return air path outlet node is the node in return air path after the mixer"""
            return_air_path_outlet_node=[node.node_name for node in airloop.return_air_path_node if node.node_type != "Inlet Node"]

           
            """ Next get zone inlet, zone, zone return node as well as nodes of all the zone level equipment after the splitter and before the mixer"""
            loops=[]
            #component_nodes=[]
            for zone_name in airloop.controlled_zone_names:
                
                """zone inlet is supply air inlet node to each zone"""
                zone_inlet=[inlet.supply_air_inlet_node for inlet in  airloop.controlled_zone_inlets if (inlet.controlled_zone_name == zone_name and inlet.number==1)]
                #print(zone_inlet)
                
                """zone return in supply air outlet node for each zone"""
                zone_return=[exhaust.exhaust_air_node_name for exhaust in airloop.controlled_zone_returns if exhaust.controlled_zone_name == zone_name]
                #print(zone_return)
                
                loop=[{"name":ele,"type":"node"} for ele in zone_inlet]+[{"name":zone_name,"type":"zone"}]+[{"name":ele,"type":"node"} for ele  in zone_return]
                #print("loop: ",loop, "\n")
                
                #Add zone equipment that has zone in zone name
                
                Zone_Equipments=[zone_equipment for zone_equipment in self.zone_equipment_component if (zone_equipment.zone_name== zone_name and zone_equipment.component_count==1)]
                #print(Zone_Equipments)
                
                
                
                for zone_equipment in Zone_Equipments:
                    zone_component=[component for component in self.component_sets if component.parent_name == zone_equipment.component_name]
                    loop=self.component_matching(zone_component)
                loops.append({zone_name:loop})
            demand_loop={"inlet_node":{"name":supply_air_path_inlet_node[0],"type":"node"},
                        "zone_loops":loops,
                        "outlet_node":{"name":return_air_path_outlet_node[0],"type":"node"}}
            airloop.demand_loop.append(demand_loop)
                        #component_nodes.append([individual_component.inlet_id,individual_component.component_name,individual_component.outlet_id])
                    
            #print("loops: ",loops)
    
    
    def assign_plantobjects_to_parents(self): 

        for branch in self.branches:
            branch.component_set=[component for component in self.component_sets if ( component.parent_type.lower() == "branch" and component.parent_name==branch.name)]
            branch.loop=self.component_matching(branch,component_list="component_set")
        
        for plantloop in [loops for loops in self.plantloops if loops.loop_type=="Supply"]:
            """assign branch list to airloops"""
            #plantloop.supplybranch=[branch for branch in self.branches if (branch.loop_name == plantloop.loop_name and plantloop.loop_type=="Supply")]
            #plantloop.demandbranch=[branch for branch in self.branches if (branch.loop_name == plantloop.loop_name and plantloop.loop_type=="Demand")]
            plantloop.supplyconnecterbranch=[branch for branch in self.loop_connecter_branches if (branch.loop_name==plantloop.loop_name and branch.loop_type=="Supply")]
            plantloop.demandconnecterbranch=[branch for branch in self.loop_connecter_branches if (branch.loop_name==plantloop.loop_name and branch.loop_type=="Demand")]  
            
            plantloop.supplyconnecternode=[node for node in self.loop_connecter_nodes if (node.loop_name==plantloop.loop_name and node.loop_type=="Supply")]
            plantloop.demandconnecternode=[node for node in self.loop_connecter_nodes if (node.loop_name==plantloop.loop_name and node.loop_type=="Demand")]  

            plantloop.supplyconnectionbranch=connection_link(plantloop.supplyconnecterbranch)
            plantloop.demandconnectionbranch=connection_link(plantloop.demandconnecterbranch)
            
            plantloop.supplyconnection=self.branchname_to_branchloop_map(plantloop.supplyconnectionbranch)
            plantloop.demandconnection=self.branchname_to_branchloop_map(plantloop.demandconnectionbranch)
                
    def branchname_to_branchloop_map(self,inputbranchlist):
        branchlist=copy.deepcopy(inputbranchlist)
        for i in range(len(branchlist)):
            if type(branchlist[i]) is str:
                branchloop=[branch.loop for branch in self.branches if branch.name == branchlist[i]][0]
                branchlist[i]=branchloop
            elif type(branchlist[i]) is list:
                for j in range(len(branchlist[i])):
                    branchloop=[branch.loop for branch in self.branches if branch.name == branchlist[i][j]][0]
                    branchlist[i][j]=branchloop                  
        return branchlist
    
    def output_json(self,filename="Output"):  
        
        output_list=[]
        for airloop in self.airloops.values():
            output_dict={}
            output_dict["name"]=airloop.name
            output_dict["type"]="airloops"
            output_dict["supply_loop"]=airloop.supply_loop
            output_dict["demand_loop"]=airloop.demand_loop
            output_list.append(output_dict)
        for plantloop in [loops for loops in self.plantloops if loops.loop_type=="Supply"]:
            output_dict={}
            output_dict["name"]=plantloop.loop_name
            output_dict["type"]="plantloops"
            output_dict["supply_loop"]=plantloop.supplyconnection
            output_dict["demand_loop"]=reverse(plantloop.demandconnection)
            output_list.append(output_dict)
        self.output=output_list   
        
        out_dir=os.getcwd()+"//Output//"
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        print(out_dir)
        print(filename)
        html_template=open("output_template.html","r")
        html=html_template.read()
        html=html.replace("ReplaceJSON",json.dumps(output_list))
        
        with open(out_dir+filename+".html","w") as file:
            file.write(str(html))
        filepath=out_dir+filename+".json"
        with open(filepath, 'w') as outfile:
            json.dump(output_list, outfile, indent=4) #, indent=4
    
    def visualize_component_sets(self):
        root = {}
        for cs in self.component_sets:
            parent = '%s (%s, %s -> %s)' % (cs.parent_name, cs.parent_type, cs.inlet_node.name, cs.outlet_node.name)
            child = '%s (%s, %s -> %s)' % (cs.component_name, cs.component_type, cs.inlet_node.name, cs.outlet_node.name)
            result = build_tree(root, parent, child)
            if not result:
                root[parent] = {child: {}}
        for k,v in root.items():
            print(k)
            print(' |')
            for sk, sv in v.items():
                #print(' +-', ' -+- '.join([el for el in v.keys()]))
                print(' +-', sk)
                if sv:
                    print('   |')
                    for ssk, ssv in sv.items():
                        #print(' +-', ' -+- '.join([el for el in v.keys()]))
                        print('   +-', ssk)
            print()

class ComponentTree:
    def __init__(self, name, type, inlet_node, outlet_node):
        self.name = name
        self.type = type
        self.inlet_node = inlet_node
        self.outlet_node = outlet_node
        self.children = []
    def match(self, other):
        return self.name == other.name and self.type == other.type and self.inlet_node == other.inlet_node and self.outlet_node == other.outlet_node
    @classmethod
    def build(cls, component_sets):
        root = []
        for cs in component_sets:
            parent_obj = cls(cs.parent_name, cs.parent_type, cs.inlet_node, cs.outlet_node)
            child_obj = cls(cs.component_name, cs.component_type, cs.inlet_node, cs.outlet_node)
            result = cls._build(root, parent_obj, child_obj)
            if not result:
                parent_obj.child = child_obj
                root.append(parent_obj)
            
    @classmethod
    def _build(cls, root, parent, child):
        for el in root:
            if el.match(parent):
                el.children.append(child)
                return True
        for el in root:
            result = cls._build(el.children, parent, child)
            if result:
                return True
        return False

def build_tree(root, parent, child):
    if parent in root:
        root[parent][child] = {}
        return True
    for v in root.values():
        result = build_tree(v, parent, child)
        if result:
            return True
    return False


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(
#         description='Generate a diagram of HVAC in an EnergyPlus model')
    
#     parser.add_argument('-o', '--output', help='write output to named file', metavar='file', default="Output")
#     parser.add_argument('BND', help='EnergyPlus BND file to process')

#     #args = parser.parse_args()
#     args = parser.parse_args([file,"-o "+output])
#     """python hvac-diagram.py Detailed_Medium_Office/Detailed_Medium_Office_OSApp_1_2_1.bnd""" #command 
#     fp = open(args.BND, 'r')
#     bnd = BranchNodeDetails(fp, merge_aliased_nodes=True)
#     bnd.read_file()
#     fp.close()

#     bnd.assign_objects_to_parents()
#     bnd.create_airloop_supply()
#     bnd.create_airloop_demand()
#     bnd.assign_plantobjects_to_parents()
#     bnd.output_json(filename=args.output)

# =============================================================================
# html_template=open("output_template.html","r")
# 
# html=html_template.read()
# html=html.replace("ReplaceJSON")
# =============================================================================

#plantloop=bnd.plantloops[5]





