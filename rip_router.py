import sys
import re
import socket
import select

"""
TODO:
    - Start the 321 assignment

    - Write a proper docstring

    - Implementation of RIP lmao

"""


class ConfigSyntaxError(Exception):
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
    intput_ports : list
        Contains all of the port numbers (unique) that represent the interfaces
        of the router that are connected to adjacent routers
    outputs : list
        Contains elements of form PortNum-Metric-ID for all adjacent routers.
        PortNum represents the interface of adjacent routers that are directly
        connected to the router.

    Methods
    -------
    read_config_file
        Opens and stores the contents of a config file given as a
        parameter on the command line.
    parse

    parse_router_id
    parse_input_ports
    parse_outputs
    check_port_num
    """
    def __init__(self):
        file_data = self.read_config_file()

        self.router_id = None
        self.input_ports = None
        self.outputs = None

        self.parse(file_data)

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
                    raise ConfigSyntaxError("ConfigSyntaxError: Config file syntax is incorrect")

        except ConfigSyntaxError as error:
            print(str(error))
            sys.exit(1)

        self.parse_router_id()
        self.parse_input_ports()
        self.parse_outputs()

    def parse_router_id(self):
        try:
            self.router_id = int(self.router_id)
            if self.router_id < 1 or self.router_id > 64000:
                raise ConfigSyntaxError("ConfigSyntaxError: Router ID must be between 1 and 64000 inclusive!")
        except ValueError:
            print("ValueError: Router Id must be an integer")
            sys.exit(1)
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)

    def parse_input_ports(self):

        for i in range(len(self.input_ports)):
            try:
                self.input_ports[i] = int(self.input_ports[i])
            except ValueError:
                print("ValueError: Value given for an input port wasn't an integer!")
                sys.exit(1)
            else:
                self.check_port_num(self.input_ports[i])
        try:
            if len(set(self.input_ports)) != len(self.input_ports):
                raise ConfigSyntaxError("ConfigSyntaxError: Input ports must be unique")
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)

    def parse_outputs(self):
        """I hate this method but can't make it less gross"""

        for i in range(len(self.outputs)):
            try:
                router = [int(x) for x in self.outputs[i].split('-')]
            except ValueError:
                print("ValueError: Outputs should only contain hyphen separated ints")
                sys.exit(1)
            else:
                try:
                    if len(router) != 3:
                        raise ConfigSyntaxError("ConfigSyntaxError: Outputs should be of form: portNum-metric-routerID")
                    else:
                        router = {'Port': router[0], 'Metric': router[1], 'ID': router[2]}
                        if router['Port'] in self.input_ports:
                            raise ConfigSyntaxError("ConfigSyntaxError: Port numbers in outputs cannot be in inputs!")
                        else:
                            self.check_port_num(router['Port'])
                except ConfigSyntaxError as err:
                    print(str(err))
                    sys.exit(1)
            self.outputs[i] = router

    def check_port_num(self, port_num):
        try:
            if port_num < 1024 or port_num > 64000:
                raise ConfigSyntaxError("ConfigSyntaxError: Port number in config is outside acceptable range")
        except ConfigSyntaxError as err:
            print(str(err))
            sys.exit(1)


class RipRouter:
    pass


def event_loop(router):
    pass


def main():

    router_config = ConfigData()
    print(router_config.router_id)
    print(router_config.input_ports)
    print(router_config.outputs)


if __name__ == "__main__":
    main()
