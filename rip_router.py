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

    Shai:
        - RIP daemon update() function
        - RIP packet construction & deconstruction


"""

UPDATE_FREQ = 30
TIMEOUT = 180
GARBAGE = 300
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
                        raise ConfigSyntaxError(
                            "Outputs should be of form: portNum-metric-routerID")
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
        self.outputs = {router[2]: router[:2] for router in self.outputs}

    def check_port_num(self, port_num):
        try:
            if port_num < 1024 or port_num > 64000:
                raise ConfigSyntaxError(
                    "ConfigSyntaxError: Port number in config is outside acceptable range")
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)


class ForwardingEntry:
    """Class to hold information on forwarding table entries"""

    def __init__(self, next_hop, port, metric):
        self.next_hop_id = next_hop
        self.next_hop_port = port
        self.metric = metric
        self.timeout_flag = 0
        self.update_timer = time()

    def __str__(self):
        return "Next hop router ID: {}\n" \
               "Next hop router port: {}\n" \
               "Metric: {}\n".format(self.next_hop_id, self.next_hop_port, self.metric)


class RipRouter:
    """Class which simulates a router with attached neighbours, message transmit/receive and a forwarding table"""

    def __init__(self, router_config):
        self.config = router_config
        self.input_sockets = []
        self.output_socket = None
        self.address = '127.0.0.1'
        self.forwarding_table = dict()
        self.start()
        self.update_timer = timer_refresh(1)

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
        own_entry = ForwardingEntry(self.config.router_id, "N/A", 0)
        self.forwarding_table[self.config.router_id] = own_entry
        logger("Forwarding table entry created for router {}:\n"
              "{}".format(self.config.router_id, own_entry))

    def update_forwarding_entry(self, router_id, entry):
        """Updates an entry to the forwarding table"""
        entry.timeout_flag = 0
        entry.update_timer = timer_refresh()
        self.forwarding_table[router_id] = entry

    def send(self, router_id, data):
        try:
            self.output_socket.sendto(
                data, (self.address, self.config.outputs[router_id][0])
        except OSError as err:
            traceback.print_exc()
            print(err)

    def remove_forwarding_entry(self, router_id):
        """Removes an entry from the forwarding table"""
        try:
            del self.forwarding_table[router_id]
        except KeyError as err:
            print("KeyError: Router {} is not in the forwarding table".format(err))


class RipDaemon:
    """RIP routing daemon which contains a router class which it controls"""

    def __init__(self, router):
        self.router=router
        self.last_update=None
        self.timing_queue=[]

    def start(self):
        while True:
            if False:
                pass
            elif False:
                pass
            else:
                try:
                    readable, _, _=select(self.router.input_sockets, [], [], timeout=None)
                    # timeout will actually be equal to something off of timing queue just not sure how to implement yet
                except OSError as err:
                    traceback.print_exc()
                    print(str(err))
                else:
                    # do the thing
                    if not readable:
                        # timeout happened do the thing
                        pass
                    else:
                        # do the other thing
                        pass

    def update(self):
        # sends update packets to all neighbouring routers
        for neighbour in self.router.config.outputs.keys():
            data=RipPacket(self.router.config.router_id,
                             self.router.forwarding_table, ).construct()
            self.router.send(data, neighbour)
        self.router.update_timer=timer_refresh(1)  # reset update timer


class RipPacket:
    def __init__(self, sourceid=None, entries=None, destinationid=None):
        self.sourceid=hostid
        # poisoned reverse, if the entry's next hop is the destination, it sets the metric to 'infinity'
        for entry in entries:
            if entry.next_hop_id == destinationid:
                entry.metric == INFINITY

        self.entries=entries

    def construct(self):
        # builds packet with the information in the object and returns a bytearray
        return None

    def deconstruct(bytearray):
        # deconstructs RIP packet and sets sourceid and entries fields


def timer_refresh(type=0):
    # type = 1 : returns a initial start time +- 0-5 seconds of offset
    # type = 2: no randomness, used for route timers
    if type == 1:
        return time() + (10 * random.randint(0, 5) - 5)
    else:
        return time()


def main():
    router_config=ConfigData()
    print(router_config)
    router=RipRouter(router_config)
    # RipDaemon(router).start


if __name__ == "__main__":
    main()
