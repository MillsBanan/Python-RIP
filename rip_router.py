import sys
import re
import socket
import select

"""
TODO:
    - Start the 320 assignment

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


class Config_Data():
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
    config_okay : boolean
        Used to represent whether or not the config file/ data supplied is valid
        (Will probably remove and add specific execptions to raise later)

    Methods
    -------
    read_config
        Opens a config file given as a parameter on the command line.
        Does very simple parsing to check that the file has the correct syntax
    """
    def __init__(self):
        file_data = self.read_config()
        self.router_id, self.input_ports, self.outputs = self.parse(file_data)
        self.config_okay = True

        self.check_router_id()
        self.process_input_ports()

    def parse(data):
        pass


    def read_config(self):
        if len(sys.argv) != 2:
            print("Invalid number of parameters given.\nUsage: stuff.")
        file_name = sys.argv[1]
        file_data = []

        with open(file_name) as file:
            for line in file:
                file_data.append(line)
        # Below code will be part of the parsing stuff
        # for line in file_data:
        #     line = re.split(', |\s', line)
        #     if line[0] in ['//', '']:
        #         continue
        #     elif line[0] == "router-id":
        #         router_id = line[1]
        #     elif line[0] == "input-ports":
        #         input_ports = line[1:-1]
        #     elif line[0] == "outputs":
        #         outputs = line[1:-1]
        #     else:
        #         print("Incorrect config file syntax!")
        return file_data

    def check_router_id(self):
        """Checks if the provided router ID is an integer between 1 and
           64000 inclusive."""

        if not isinstance(self.router_id, int):
            print("Router ID provided is not an integer!")
            self.config_okay = False
        elif 1 >= self.router_id >= 64000:
            print("Router ID must be between 1 and 64000 inclusive!")
            self.config_okay = False

    def port_num_valid(self, port_num):

        if 1024 >= input_ports[i] >= 64000:
            print("Port number in config is outside acceptable range!")
            return False
        else:
            return True

    def process_input_ports(self):
        for i in range(self.input_ports):
            try:
                self.input_ports[i] = int(self.input_ports[i])
                if not port_num_valid(self.input_ports[i]):
                    self.config_okay = False
                    break
            except ValueError:
                print("Value given for an input port isn't an integer!")
                self.config_okay = False
                break
        if len(set(self.input_ports)) != len(self.input_ports):
            print("Bruh you need unique port nums!")
            self.config_okay = False

    def process_outputs(self):
        for router in self.outputs:
            try:
                router = [int(x) for x in router.split('-')]
            except ValueError:
                print("Outputs should be of form: portNum-metric-routerID, all of type int")
                self.config_okay = False
            else:
                router = {'Port' : router[0], 'Metric' : router[1], 'ID' : router[2]}
                if router['Port'] in self.input_ports:
                    print("Port numbers in outputs cannot be in inputs!")
                    self.config_okay = False
                    break
                if not port_num_valid(router['Port']):
                    self.config_okay = False
                    break


def router_setup(router_id, input_ports, output_ports, neighbours):
    pass


def router_loop():
    pass

def main():

    router_config = Config_Data()
    if not router_config.config_okay:
        print("You blew it!")

    #router_setup(router_id, input_ports, outputs, neighbours)

if __name__ == "__main__":
    main()
