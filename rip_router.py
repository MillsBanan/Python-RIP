import sys
import re
import socket
import select

"""
TODO:
    - Start the 321 assignment

    - Write a proper docstring

    - finish the Config_Data class
        - Write something that looks like an actual parser for the config data
        that actually checks syntax properly

        - Proper error handling for Config_Data, raising actual exceptions and not
        just print statements. Also potentially writing an error class specific to
        config data. Mainly so that we don't use the stupid attribute config_okay
        cause it's a hacky AF.

    - Implementation of RIP lmao

"""

class ConfigSyntaxError(Exception):
    pass

class Config_Data:
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
    read_config
        Opens and stores the contents of a config file given as a
        parameter on the command line.
    """
    def __init__(self):
        file_data = self.read_config()

        self.router_id = None
        self.input_ports = None
        self.outputs = None

        self.parse(file_data)


    def parse(self, file_data):

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
                raise ConfigSyntaxError("Config file has incorrect syntax")

        self.parse_router_id()
        self.parse_input_ports()
        self.parse_outputs()

    def read_config(self):

        if len(sys.argv) != 2:
            print("Incorrect number of parameters given on command line.")
            print("USAGE: rip_router.py config.txt")
            sys.exit(1) # Program failure, wrong number of args given on CLI

        file_name = sys.argv[1]
        file_data = []

        with open(file_name) as file:
            for line in file:
                file_data.append(line)
        return file_data

    def parse_router_id(self):
        try:
            self.router_id = int(self.router_id)
        except ValueError:
            raise ValueError("Router Id must be an integer")
            sys.exit(1)
        else:
            if 1 >= self.router_id >= 64000:
                raise ConfigSyntaxError("Router ID must be between 1 and 64000 inclusive!")
                sys.exit(1)
    def check_port_num(self, port_num):

        if 1024 >= port_num >= 64000:
            raise ConfigSyntaxError("Port number in config is outside acceptable range")
            sys.exit(1)

    def parse_input_ports(self):

        for i in range(len(self.input_ports)):
            try:
                self.input_ports[i] = int(self.input_ports[i])
            except ValueError:
                raise ValueError("Value given for an input port isn't an integer!")
                sys.exit(1)
            else:
                self.check_port_num(self.input_ports[i])

        if len(set(self.input_ports)) != len(self.input_ports):
            raise ConfigSyntaxError("Input ports must be unique")
            sys.exit(1)

    def parse_outputs(self):
        """I hate this method but can't make it less gross"""

        for i in range(len(self.outputs)):
            try:
                router = [int(x) for x in self.outputs[i].split('-')]
            except ValueError:
                raise ValueError("Outputs should only contain hyphen separated ints")
                sys.exit(1)
            else:
                if len(router) != 3:
                    raise ConfigSyntaxError("Outputs should be of form: portNum-metric-routerID")
                    sys.exit(1)
                else:
                    router = {'Port' : router[0], 'Metric' : router[1], 'ID' : router[2]}
                    if router['Port'] in self.input_ports:
                        raise ConfigSyntaxError("Port numbers in outputs cannot be in inputs!")
                        sys.exit(1)
                    else:
                        self.check_port_num(router['Port'])

            self.outputs[i] = router


class RipRouter:
    pass


def main():

    router_config = Config_Data()
    print(router_config.router_id)
    print(router_config.input_ports)
    print(router_config.outputs)
    #router_setup(router_id, input_ports, outputs, neighbours)

if __name__ == "__main__":
    main()
