import sys
import re
import socket
from select import select
from time import time
import random
import copy

"""
    A simple implementation of the RIP protocol using python.
    
    Authors:
        Shai Levin
        Ryan Miller: 18392825
    
    Date:
        04/05/20
    
"""

UPDATE_FREQ = 10
TIMEOUT = UPDATE_FREQ * 6
GARBAGE = UPDATE_FREQ * 4
INFINITY = 16
ENABLE_LOGGER = 1
START_TIME = time()  # start time (useful for logger function)


def logger(message, showtime=0):
    """
    Logger function which can easily be enabled or disabled for printing logging information
    """
    if ENABLE_LOGGER:
        if showtime == 1:
            print("{:.2f}s : ".format((time() - START_TIME)) + message)
        else:
            print(message)


class ConfigSyntaxError(Exception):
    """
    A class to raise errors related to config file syntax
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "ConfigSyntaxError:" + self.message + "\n"


class ConfigData:
    """
    A class used to read and store router configuration data.

    Attributes
    ----------
    router_id (int): Unique ID for the router in the network
    input_ports (list): Contains unique port numbers to listen on for each adjacent router
    outputs (list): Contains elements of form PortNum-Metric-ID for sending data to each adjacent router.
                    Is transformed into a dict by self.parse_outputs().
    """
    def __init__(self):
        """Reads and parses config file given on CLI, transforms config data into useful objects for later use."""
        file_data = self.read_config_file()
        self.router_id = None
        self.input_ports = None
        self.outputs = None
        self.parse(file_data)

    def __str__(self):
        return "+============ ROUTER {} CONFIGURATION ============+\n" \
               "  Input ports -> {}\n" \
               "  Outputs -> {}\n" \
               "+================================================+\n".format(self.router_id,
                                                                             self.input_ports, self.outputs)

    def read_config_file(self):
        """Opens and stores the contents of the config file given as a parameter on the command line.

            Returns:
                File_data: List of all of the lines in the config file read if successful
        """
        if len(sys.argv) != 2:
            print("Incorrect number of parameters given on command line.")
            print("USAGE: rip_router.py config1.txt")
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
        """Performs basic syntax parsing over the config file. Stores config data to relevant attributes of self.

            Args:
                file_data: List of all of the lines in the config file

        """
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
        """Checks if the given router ID is an integer and within the accepted range."""
        try:
            self.router_id = int(self.router_id)
            if self.router_id < 1 or self.router_id > 64000:
                raise ConfigSyntaxError("Router ID must be between 1 and 64000 inclusive!")
        except ValueError:
            print("ConfigSyntaxError: Router Id must be an integer")
            sys.exit(1)
        except ConfigSyntaxError as err:
            print(err)
            sys.exit(1)

    def parse_input_ports(self):
        """Checks if the given input ports are distinct integers and within the accepted range."""
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
        """Parses outputs. Changes self.outputs to a dict with entries of the form -> Router ID: [Port Num, Metric]"""
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
                        raise ConfigSyntaxError("Output: {}. "
                                                "Outputs should be of form: portNum-metric-routerID.".format(router))
                    else:
                        if router[0] in self.input_ports:
                            raise ConfigSyntaxError("Output: {}. "
                                                    "Port numbers in outputs cannot be in inputs!".format(router))
                        elif router[2] < 1 or router[2] > 15:
                            raise ConfigSyntaxError("Output: {}. "
                                                    "Metrics must be between 1 and 15 inclusive!".format(router))
                        else:
                            self.check_port_num(router[0])
                except ConfigSyntaxError as err:
                    print(str(err))
                    sys.exit(1)
        try:
            if len({router[0] for router in self.outputs}) != len(self.outputs):
                raise ConfigSyntaxError("Port numbers in outputs must be unique!")
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)
        self.outputs = {router[2]: router[:2] for router in self.outputs}

    def check_port_num(self, port_num):
        """Checks if the given port number is within the range 1024 - 64000."""
        try:
            if port_num < 1024 or port_num > 64000:
                raise ConfigSyntaxError("Port: {}. "
                                        "ConfigSyntaxError: Port number in config is outside acceptable range".format(port_num))
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)


class RipRouter:
    """A class to simulate a router controllable by an instance of the class RipDaemon

        Attributes
        ----------
        config (ConfigData): Holds the configuration data for the router
        input_sockets (list): Contains all sockets that the router will listen on for incoming data from neighbour routers.
        output_socket (socket): Socket that will be used to send data to neighbour routers. Can be arbitrarily
                                chosen from input_sockets.
        address (str): Holds address used to bind sockets. Should always be localhost for this implementation.
        forwarding_table (dict): Stores entries for all known destinations in the network.
                                 Entries have form -> Router ID of destination: ForwardingEntry

    """
    def __init__(self, router_config):
        """Sets config to router_config, and other attributes to default values then starts itself."""
        self.config = router_config
        self.input_sockets = []
        self.output_socket = None
        self.address = '127.0.0.1'
        self.forwarding_table = dict()
        self.start()

    def start(self):
        """Creates, binds, and appends sockets to input_sockets for all input ports. Sets output_socket."""
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
        """Updates an entry in the forwarding table, adds entry if it doesn't exist

            Args:
                router_id (int): Router ID of destination     entry (ForwardingEntry): Updated or new forwarding entry
                timeout (int): Timeout flag for entry, dfault 0.
                    A simple implementation of the RIP protocol.
        """
        logger("Updating forwarding table entry for destination {}".format(router_id), 1)
        entry.timeout_flag = timeout
        entry.update_timer = timer_refresh()
        self.forwarding_table[router_id] = entry

    def send(self, router_id, packet):
        """Sends packet to the appropriate port to reach the destination router.

            Args:
                router_id (int): Router ID of the destination router for the packet
                packet (bytearray): Packet containing an RIP response message or triggered update

        """
        try:
            self.output_socket.sendto(packet, (self.address, self.config.outputs[router_id][0]))
        except OSError as err:
            logger("Unable to send packet to {}.".format(router_id), 1)
            print(err)

    def remove_forwarding_entry(self, router_id):
        """Removes an entry from the forwarding table if it exists

            Args:
                router_id (int): Key of entry in forwarding table to be removed

        """
        try:
            logger("Router {} has been unreachable for too long, removing route..".format(router_id), 1)
            del self.forwarding_table[router_id]
        except KeyError as err:
            print("KeyError: Router {} is not in the forwarding table".format(err))

    def print_forwarding_table(self):
        """Prints the contents of the forwarding table in ascending order of Router IDs"""
        logger("+========= ROUTER {} FORWARDING TABLE ===========+".format(self.config.router_id))
        logger("| ID | NEXT HOP | METRIC | TIMEOUT FLAG | TIMER |")
        logger("+----|----------|--------|--------------|-------+")
        for key in sorted(self.forwarding_table):
            entry = self.forwarding_table[key]
            logger("| {}  |".format(key) + str(entry))
            logger("+----|----------|--------|--------------|-------+")
        logger("+===============================================+\n")


class ForwardingEntry:
    """A class to hold the values in the RipRouter forwarding table

        Attributes
        ----------
        next_hop_id (int): Router ID of the next hop used to get to destination
        metric (int): Int between 1 and 15 inclusive, represents the cost to destination
        timeout_flag (int): Flag is set to 1 when update_timer - current time > TIMEOUT, default 0
        update_timer (float): Holds a timestamp of when the forwarding entry was last updated

    """
    def __init__(self, next_hop, metric):
        """Sets relevant attributes to given args and others to default values."""
        self.next_hop_id = next_hop
        self.metric = metric
        self.timeout_flag = 0
        self.update_timer = timer_refresh()

    def __str__(self):
        return "    {}     |    {}   |      {}       |   {}   |".format(self.next_hop_id, self.metric,
                                                                        self.timeout_flag, int(time() - self.update_timer))


class RipError(Exception):
    """
    A class to raise errors related to RIP
    """

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return str(self.message)


class RipDaemon:
    """A class implementation of a basic RIP daemon, controls an instance of RipRouter.

        Attributes:
            router (RipRouter): Router that the daemon will control
            last_update (float): Timestamp of the last time scheduled update was done
            triggered_update (float): Default of -1 when no triggered update is to be sent or
                                      float between 1 and 5 that delays when the triggered update is sent

    """
    def __init__(self, router):
        """Sets self.router to router, sets other attributes to default, sends update to neighbours, start event loop"""
        self.router = router
        self.update()
        self.last_update = timer_refresh(1)
        self.triggered_update = -1  # timer for triggered updates
        logger("RIP Daemon initialized. Starting routing loop\n", 1)
        self.event_loop()

    def event_loop(self):
        """Infinite loop, handles all RIP events specific to this implementation"""
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
                if entry.timeout_flag == 0 and (
                        current_time - entry.update_timer) > TIMEOUT:  # if timer exceeds TIMEOUT
                    entry.metric = INFINITY
                    self.router.update_forwarding_entry(destination, entry, 1)
                    self.router.print_forwarding_table()
                    self.schedule_triggered_update()
                elif entry.timeout_flag == 1 and \
                        (current_time - entry.update_timer) > GARBAGE:  # if timer exceeds GARBAGE
                    self.router.remove_forwarding_entry(destination)
                    self.router.print_forwarding_table()
                    break  # this stops iteration after the dictionary has changed size, prevents error
            # INPUT SOCKET HANDLER #
            try:
                readable, _, _ = select(self.router.input_sockets, [], [], 1)  # select timeout of 1 second.
            except OSError as err:
                print(str(err))
            else:
                if not readable:  # timout occurred
                    continue
                else:  # data was received
                    for sock in readable:
                        packet = sock.recv(512)
                        self.process_input(packet)

    def update(self):
        """Sends update packets to all neighbouring routers"""
        self.router.print_forwarding_table()
        logger("Sending routing update to neighbouring routers...", 1)
        for neighbour in self.router.config.outputs.keys():
            packet = RipPacket(self.router.config.router_id,
                               copy.deepcopy(self.router.forwarding_table), neighbour).construct()
            self.router.send(neighbour, packet)

    def process_input(self, packet):
        """Processes packet, drops the packet if it came from a non neighboured router, does DV calcs otherwise
                Args:
                    packet (bytearray): Packet received on one of the routers inputs
        """
        sourceid, entries = RipPacket().deconstruct(packet)
        if sourceid is not None and entries is not None:  # valid packet received
            try:
                if sourceid not in self.router.config.outputs.keys():  # came from a non-neighboured router
                    raise RipError(
                        "Router received a packet from Router {} which is not a neighbour router".format(sourceid))
                # include a forwarding entry for the router which sent the packet
                entries[sourceid] = ForwardingEntry(sourceid, 0)

                for destination in entries.keys():  # does DV calcs for each entry in packet
                    self.update_routes(sourceid, destination, entries[destination])
            except RipError as err:
                print(str(err))
                logger("Dropping packet...")

    def schedule_triggered_update(self):
        """Sets self.triggered_update to a float between 1-5"""
        due_in = ((UPDATE_FREQ/7.5) * random.random() + 1)
        self.triggered_update = time() + due_in  # set triggered update timer 1-5 seconds
        logger("Triggered update scheduled in {:.2f} seconds.".format(due_in), 1)

    def update_routes(self, source_id, destination, route):
        """Determines if route is better than the already known route in the forwarding table
                Args:
                    source_id (int): Router ID of the source of the route
                    destination (int): Router ID of where the route points to
                    route (ForwardingEntry): Candidate forwarding entry to be added to table

        """
        if destination != self.router.config.router_id:  # prevents adding self to forwarding table
            added_cost = self.router.config.outputs[route.next_hop_id][1]
            # adds link cost to each entries metric
            route.metric = min(added_cost + route.metric, INFINITY)
            if destination in self.router.forwarding_table.keys():  # if destination is already in forwarding table
                if self.router.forwarding_table[destination].next_hop_id == source_id:
                    # if next hop is the sender of the new route
                    if route.metric == INFINITY and self.router.forwarding_table[destination].metric != INFINITY:
                        self.router.update_forwarding_entry(destination, route, 1)  # set route to 1
                        self.schedule_triggered_update()
                    else:  # the route via the same next_hop has changed to a different metric
                        self.router.update_forwarding_entry(destination, route)
                elif self.router.forwarding_table[destination].metric > route.metric:
                    self.router.update_forwarding_entry(destination, route)
            elif route.metric < INFINITY:
                self.router.update_forwarding_entry(destination, route)


class RipPacket:
    """A class to construct, deconstruct and validate RIP packets.

            Attributes
            ----------
            source_id (int): Router ID of creator of the packet, default None
            entries (dict): Copy of creators forwarding table, default None
            destination (int): Router ID of the intended recipient of the packet, default None

    """
    def __init__(self, sourceid=None, entries=None, destinationid=None):
        """Set's relevant attributes to args, sets route metrics to infinity when applicable"""
        self.sourceid = sourceid
        # poisoned reverse, if the entry's next hop is the destination, it sets the metric to 'infinity'
        if entries is not None:
            for router_id in entries.keys():
                if entries[router_id].next_hop_id == destinationid:
                    entries[router_id].metric = INFINITY
        self.entries = entries

    def construct(self):
        """Constructs an RIP packet

                Returns:
                    packet (bytearray): RIP packet ready to send

        """
        packet = [2, 2]  # packet type is always 2, and version is always 2
        # 3rd & 4th bytes are now senders router ID
        packet += [self.sourceid >> 8, self.sourceid & 0xFF]
        for router_id, item in self.entries.items():
            packet += self.construct_rip_entry(router_id, item.metric)
        return bytearray(packet)

    def construct_rip_entry(self, router_id, metric):
        """Formats entry data ready to append to an RIP packet

                Args:
                    router_id (int): Router ID of where the entry route will point to
                    metric (int): Metric of route

                Returns:
                     list : entry ready to append to an RIP packet

        """
        return [0, 2, 0, 0,  # AFI = 2 for IP
                0, 0, router_id >> 8, router_id & 0xFF,  # router_id is only 16 bits
                0, 0, 0, 0,
                0, 0, 0, 0,
                metric >> 24, (metric >> 16) & 0xFF, (metric >> 8) & 0xFF, metric & 0xFF]

    def deconstruct(self, packet):
        """Deconstructs and validates an RIP packet
                Args:
                    packet (bytearray): RIP packet

                Returns:
                      None, None : If packet is invalid
                      source_id (int), entries (dict) : Creator of packet, copy of senders forwarding table if it exists
                                                        and packet is valid.

        """
        if len(packet) < 4:  # Packet is smaller than RIP header
            logger("Packet size is less than minimum. Dropping packet...\n")
            return None, None
        elif not self.header_valid(packet):
            logger("Invalid packet received. Dropping packet...\n")
            return None, None
        else:
            entries = dict()
            source_id = (packet[2] << 8) + packet[3]
            payload = packet[4:]
            if len(payload) % 20 != 0:
                logger("Packet payload contains 1 or more entries of incorrect size. Dropping packet...\n")
                return None, None
            else:
                i, j = 0, 20  # used for slicing the bytearray, will always cover 20 bytes of the bytearray
                for _ in range(len(payload) // 20):
                    entry, router_id = self.deconstruct_rip_entry(payload[i:j], source_id)
                    if not entry:
                        logger("Packet {} contained invalid entry. Dropping packet...\n".format(packet))
                        return None, None
                    else:
                        entries[router_id] = entry
                        i = j
                        j += 20
                return source_id, entries

    def deconstruct_rip_entry(self, entry, next_hop):
        """Deconstructs and validates an RIP entry

                Args:
                    entry (bytearray): Bytearray containing entry data
                    next_hop (int): The next hop for the entry

                Returns:
                    None, None : If entry is invalid
                    ForwardingEntry, router_id (int) : A forwarding entry for the data contained in the packet entry and
                                                       the router_id that the entry points to if the packet is valid.

        """
        if not self.entry_valid(entry):
            return None, None
        else:
            metric = entry[19]
            router_id = (entry[6] << 8) + entry[7]
            return ForwardingEntry(next_hop, metric), router_id

    def header_valid(self, header):
        """Validates the header of an RIP packet
                Args:
                    header (bytearray): Bytearray containing RIP packet header

                Returns:
                      True : If header is valid
                      False : otherwise

        """
        if not (header[0] == 2 and header[1] == 2):
            return False
        else:
            return True

    def entry_valid(self, entry):
        """Validate an entry in an RIP packet
                Args:
                    entry (bytearray): Bytearray containing an RIP entry

                Returns:
                      True: If entry is valid
                      False: otherwise
        """
        if not (entry[1] == 2 and  # AFI must equal 2
                entry[2] + entry[3] == 0 and  # Bytes 2, 3 must both be zero
                entry[8] + entry[9] + entry[10] + entry[11] == 0 and  # Bytes 8, 9, 10, 11 must all be zero
                entry[12] + entry[13] + entry[14] + entry[15] == 0):  # Bytes 12, 13, 14, 15 must all be zero
            return False
        else:
            return True


def timer_refresh(type=0):
    # type = 1 : returns a initial start time +- 0-5 seconds of offset
    # type = 2: no randomness, used for route timers
    if type == 1:
        randomshift = (2*(UPDATE_FREQ/6) * random.random() - (UPDATE_FREQ/6))
        return time() + randomshift
    else:
        return time()


def main():
    router_config = ConfigData()
    print(router_config)
    router = RipRouter(router_config)
    RipDaemon(router)


if __name__ == "__main__":
    main()
