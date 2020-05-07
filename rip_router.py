import sys
import re
import socket
import traceback
from select import select
from time import time
import random

"""
TODO:

    - Write a proper docstring
    - Implementation of RIP lmao
    - bruh we need to do a check that the metric in the config is between 1 and 15
    - also maybe a check in the forwardingtable class when you init, that validates metric size?

    Shai:
        - RIP daemon update() function
        - RIP packet construction & deconstruction


"""

UPDATE_FREQ = 10
TIMEOUT = UPDATE_FREQ * 6
GARBAGE = UPDATE_FREQ * 4
INFINITY = 16
ENABLE_LOGGER = 1


def logger(message):
    """
    Logger function which can easily be enabled or disabled for printing logging information
    """
    if ENABLE_LOGGER:
        print(message)


class ConfigSyntaxError(Exception):
    """
    A class to raise errors related to config file syntax
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "ConfigSyntaxError:" + self.message + "\n"


class RouterError(Exception):
    """
    A class to raise custom errors
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


class ConfigData:
    """
    A class used to read and store router configuration data.

    Attributes
    ----------
    router_id : int
        Unique ID for the router in the network
    input_ports : list
        Contains all of the port numbers (unique) that represent the interfaces
        of the router that are connected to adjacent routers
    outputs : list
        Contains elements of form PortNum-Metric-ID for each router 'R' adjacent to router 'A'.
        PortNum represents the interface that router R is connected to router A over.
        Metric is the cost of the link from A to R.
        ID is the router ID of router R.

    Methods
    -------
    read_config_file
        Opens and stores the contents of the config file given as a
        parameter on the command line.
    parse
        Performs basic parsing over the contents of the config file making sure that it follows the basic syntax
        given below for config files. Stores relevant lines to the appropriate attributes of current ConfigData object
        then makes calls to the parse_* methods below.
    parse_router_id
        Checks if the given router ID is an integer and within the accepted range.
    parse_input_ports
        Checks if the given input ports are distinct integers and within the accepted range.
    parse_outputs
        Checks if the given outputs are hyphen separated integers
    check_port_num
    """

    def __init__(self):
        file_data = self.read_config_file()
        self.router_id = None
        self.input_ports = None
        self.outputs = None
        self.parse(file_data)

    def __str__(self):
        return "Configuration set for router {}:\n" \
               "Input ports: {}\n" \
               "Outputs: {}\n".format(self.router_id, self.input_ports, self.outputs)

    def read_config_file(self):
        if len(sys.argv) != 2:
            print("Incorrect number of parameters given on command line.")
            print("USAGE: rip_router.py config.txt")
            sys.exit(1)  # Program failure, wrong number of args given on CLI
        file_name = sys.argv[1]
        file_data = []
        try:
            with open(file_name) as f:
                for line in f:
                    file_data.append(line)
        except FileNotFoundError as err:
            print("FileNotFoundError: {0}".format(err))
            sys.exit(1)
        return file_data

    def parse(self, file_data):
        try:
            for line in file_data:
                line = re.split(', |\s', line)
                if line[0] in ['//', '']:
                    continue
                elif line[0] == "router-id":
                    self.router_id = line[1]
                elif line[0] == "input-ports":
                    self.input_ports = line[1:-1]
                elif line[0] == "outputs":
                    self.outputs = line[1:-1]
                else:
                    raise ConfigSyntaxError("Config file syntax is incorrect")
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)
        self.parse_router_id()
        self.parse_input_ports()
        self.parse_outputs()
        try:
            if None in [self.router_id, self.outputs, self.input_ports]:
                raise ConfigSyntaxError("Config file syntax is incorrect")
            elif len(self.input_ports) == 0 or len(self.outputs) == 0:
                raise ConfigSyntaxError("Can't have no input ports or no output ports")
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)

    def parse_router_id(self):
        try:
            self.router_id = int(self.router_id)
            if self.router_id < 1 or self.router_id > 64000:
                raise ConfigSyntaxError("Router ID must be between 1 and 64000 inclusive!")
        except ValueError:
            traceback.print_exc()
            print("ConfigSyntaxError: Router Id must be an integer")
            sys.exit(1)
        except ConfigSyntaxError as err:
            traceback.print_exc()
            print(err)
            sys.exit(1)

    def parse_input_ports(self):
        for i in range(len(self.input_ports)):
            try:
                self.input_ports[i] = int(self.input_ports[i])
            except ValueError as err:
                print(str(err))
                sys.exit(1)
            else:
                self.check_port_num(self.input_ports[i])
        try:
            if len(set(self.input_ports)) != len(self.input_ports):
                raise ConfigSyntaxError("Input ports must be unique")
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)

    def parse_outputs(self):
        for i in range(len(self.outputs)):
            try:
                router = [int(x) for x in self.outputs[i].split('-')]
                self.outputs[i] = router
            except ValueError as err:
                print(str(err))
                sys.exit(1)
            else:
                try:
                    if len(router) != 3:
                        raise ConfigSyntaxError("Outputs should be of form: portNum-metric-routerID")
                    else:
                        if router[0] in self.input_ports:
                            raise ConfigSyntaxError("Port numbers in outputs cannot be in inputs!")
                        else:
                            self.check_port_num(router[0])
                except ConfigSyntaxError as err:
                    print(str(err))
                    sys.exit(1)
        try:
            if len({router[0] for router in self.outputs}) != len(self.outputs):
                raise ConfigSyntaxError("Port numbers in outputs should be unique")
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)
        print(self.outputs)
        self.outputs = {router[2]: router[:2] for router in self.outputs}

    def check_port_num(self, port_num):
        try:
            if port_num < 1024 or port_num > 64000:
                raise ConfigSyntaxError("ConfigSyntaxError: Port number in config is outside acceptable range")
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)


class ForwardingEntry:
    """Class to hold information on forwarding table entries"""

    def __init__(self, next_hop, metric):
        self.next_hop_id = next_hop
        self.metric = metric
        self.timeout_flag = 0
        self.update_timer = timer_refresh()

    def __str__(self):
        return str(self.metric) + str(self.next_hop_id) + str(self.timeout_flag) + str(self.update_timer)


class RipRouter:
    """Class which simulates a router with attached neighbours, message transmit/receive and a forwarding table"""

    def __init__(self, router_config):
        self.config = router_config
        self.input_sockets = []
        self.output_socket = None
        self.address = '127.0.0.1'
        self.forwarding_table = dict()
        self.start()

    def start(self):
        """Binds input sockets and sets the output socket to the first input socket (if it exists)"""
        for input_port in self.config.input_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind((self.address, input_port))
                self.input_sockets.append(sock)
            except OSError as err:
                print(str(err))
                sys.exit(1)
        self.output_socket = self.input_sockets[0]
        self.print_forwarding_table()

    def update_forwarding_entry(self, router_id, entry, timeout=0):
        """Updates an entry to the forwarding table"""
        entry.timeout_flag = timeout
        entry.update_timer = timer_refresh()
        self.forwarding_table[router_id] = entry

    def send(self, router_id, data):
        try:
            self.output_socket.sendto(data, (self.address, self.config.outputs[router_id][0]))
        except OSError as err:
            traceback.print_exc()
            print(err)

    def remove_forwarding_entry(self, router_id):
        """Removes an entry from the forwarding table"""
        try:
            del self.forwarding_table[router_id]
        except KeyError as err:
            print("KeyError: Router {} is not in the forwarding table".format(err))

    def print_forwarding_table(self):
        logger("+================= FORWARDING TABLE ==================+")
        logger("| ID | AFI | NEXT HOP | METRIC | TIMEOUT FLAG | TIMER |")
        logger("+----|-----|----------|--------|--------------|-------+")
        for key in self.forwarding_table.keys():
            entry = self.forwarding_table[key]
            logger(entry)
            logger("+----|-----|----------|--------|--------------|-------+")
        logger("+=====================================================+")


class RipDaemon:
    """RIP routing daemon which contains a router class which it controls"""

    def __init__(self, router):
        self.router = router
        self.update()
        self.last_update = timer_refresh(1)
        self.triggered_update = -1  # timer for triggered updates
        logger("RIP Daemon initialized, starting event loop..")
        self.event_loop()

    def event_loop(self):
        while True:
            current_time = time()
            # SCHEDULED AND TRIGGERED UPDATE HANDLER #
            if (current_time - self.last_update) > UPDATE_FREQ or \
                    ((current_time - self.triggered_update) > 0 and not self.triggered_update == -1):
                self.update()
                self.last_update = timer_refresh(1)
                self.triggered_update = -1  # set to -1 until another triggered update event occurs

            # TIMEOUT AND GARBAGE HANDLER #
            for destination, entry in self.router.forwarding_table.items():  # iterate through forwarding table
                if entry.timeout_flag == 0 and \
                        (entry.update_timer - current_time) > TIMEOUT:  # if timer exceeds TIMEOUT
                    entry.metric = INFINITY
                    self.router.update_forwarding_entry(destination, entry, 1)
                    self.schedule_triggered_update()
                elif entry.timeout_flag == 1 and \
                        (entry.update_timer - current_time) > GARBAGE:  # if timer exceeds GARBAGE
                    self.router.remove_forwarding_entry(destination)

            # INPUT SOCKET HANDLER #
            try:
                readable, _, _ = select(self.router.input_sockets, [], [], 1)
                # timeout will actually be equal to something off of timing queue just not sure how to implement yet
            except OSError as err:
                traceback.print_exc()
                print(str(err))
            else:
                if not readable:
                    continue
                else:
                    for sock in readable:
                        packet = sock.recv(512)
                        self.process_input(packet)

    def update(self):
        # sends update packets to all neighbouring routers
        logger("Sending routing update to neighbouring routers:")
        self.router.print_forwarding_table()
        for neighbour in self.router.config.outputs.keys():
            packet = RipPacket(self.router.config.router_id,
                               self.router.forwarding_table, ).construct()
            self.router.send(neighbour, packet)

    def process_input(self, packet):
        # process a packet which has been received in one of the input buffers
        sourceid, entries = RipPacket().deconstruct(packet)
        if sourceid is not None and entries is not None:  # valid packet received
            try:
                if sourceid not in self.router.config.outputs.keys():
                    raise RouterError(
                        "Router received a packet from Router {} which is not a neighbour router".format(sourceid))
                # include a forwarding entry for the router which sent the packet
                entries[sourceid] = ForwardingEntry(sourceid, 0)

                for destination in entries.keys():  # check for each entry if its better than what we got
                    self.update_routes(sourceid, destination, entries[destination])
            except RouterError as err:
                print(str(err))

    def schedule_triggered_update(self):
        self.triggered_update = time() + (4 * random.random() + 1)  # set triggered update timer 1-5 seconds

    def update_routes(self, sourceid, destination, route):
        if destination != self.router.config.router_id:  # prevents adding self to forwarding table
            added_cost = self.router.config.outputs[route.next_hop_id][1]
            # adds link cost to each entries metric
            route.metric = min(added_cost + route.metric, INFINITY)
            if destination in self.router.forwarding_table.keys():  # if destination is already in forwarding table
                if self.router.forwarding_table[destination].next_hop_id == sourceid:
                    # if next hop is the sender of the new route
                    if route.metric == INFINITY:  # a route no longer exists
                        self.router.update_forwarding_entry(destination, route, 1)  # set route to 1
                        self.schedule_triggered_update()
                    else:  # the route via the same next_hop has changed to a different metric
                        self.router.update_forwarding_entry(destination, route)
                elif self.router.forwarding_table[destination].metric >= route.metric:
                    self.router.update_forwarding_entry(destination, route)

            elif route.metric < INFINITY:
                self.router.update_forwarding_entry(destination, route)


class RipPacket:
    def __init__(self, sourceid=None, entries=None, destinationid=None):
        self.sourceid = sourceid
        # poisoned reverse, if the entry's next hop is the destination, it sets the metric to 'infinity'
        if entries is not None:
            for router_id in entries.keys():
                if entries[router_id].next_hop_id == destinationid:
                    entries[router_id].metric = INFINITY

        self.entries = entries

    def construct(self):

        # builds packet with the information in the object and returns a bytearray
        packet = [2, 2]  # packet type is always 2, and version is always 2
        # 3rd & 4th bytes are now senders router ID
        packet += [self.sourceid >> 8, self.sourceid & 0xFF]
        for router_id, info in self.entries.items():
            packet += self.construct_rip_entry(router_id, info)
        return bytearray(packet)

    def construct_rip_entry(self, router_id, info):
        return [0, 2, 0, 0,  # AFI = 2 for IP
                0, 0, router_id >> 8, router_id & 0xFF,  # router_id is only 16 bits
                0, 0, 0, 0,
                0, 0, 0, 0,
                info.metric >> 24, (info.metric >> 16) & 0xFF, (info.metric >> 8) & 0xFF, info.metric & 0xFF]

    def deconstruct(self, packet):
        # deconstructs RIP packet and sets & returns source id and entries fields
        if len(packet) < 4:
            logger("Packet size is less than minimum. Dropping packet...")
            return None, None
        elif not self.header_valid(packet):
            logger("Invalid packet received. Dropping packet...")
            return None, None
        else:
            entries = dict()
            source_id = (packet[2] << 8) + packet[3]
            payload = packet[4:]
            if len(payload) % 20 != 0:
                logger("Packet payload contains 1 or more entries of incorrect size. Dropping packet...")
                return None, None
            else:
                i, j = 0, 19  # used for slicing the bytearray, will always cover 20 bytes of the bytearray
                for _ in range(len(payload) // 20):
                    entry, router_id = self.deconstruct_rip_entry(payload[i:j], source_id)
                    if not entry:
                        logger("Packet {} contained invalid entry. Dropping packet...".format(packet))
                        return None, None
                    else:
                        entries[router_id] = entry
                        i = j
                        j += 20
                return source_id, entries

    def deconstruct_rip_entry(self, entry, next_hop):
        if not self.entry_valid(entry):
            return None, None
        else:
            metric = entry[19]
            router_id = entry[6] << 8 + entry[7]
            return ForwardingEntry(next_hop, metric), router_id

    def header_valid(self, header):
        if not (header[0] == 2 and header[1] == 2):
            return False
        else:
            return True

    def entry_valid(self, entry):
        if not (entry[1] == 2 and
                entry[2] + entry[3] == 0 and
                (1 < entry[4] << 8 + entry[5] < 64000) and
                entry[6] + entry[7] + entry[8] + entry[9] == 0 and
                entry[10] + entry[11] + entry[12] + entry[13] == 0):
            return False
        else:
            return True


def timer_refresh(type=0):
    # type = 1 : returns a initial start time +- 0-5 seconds of offset
    # type = 2: no randomness, used for route timers
    if type == 1:
        return time() + (10 * random.random() - 5)
    else:
        return time()


def main():
    router_config = ConfigData()
    print(router_config)
    router = RipRouter(router_config)
    RipDaemon(router)


if __name__ == "__main__":
    main()
