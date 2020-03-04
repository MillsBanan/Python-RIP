import sys
import re
import socket

def config_setup():

    if len(sys.argv != 2):
        print("Please only give me one argument!")

    router_id, input_ports, outputs = None, None, None
    file_name = sys.argv[1]

    with open(file_name) as file:
        for line in file:
            line = re.split(', | ', line)
            if line[0] == '//':
                continue
            else if line[0] == "router-id":
                router_id = line[1]
            else if line[0] == "input-ports":
                input_ports = line[1:]
            else if line[0] == "outputs":
                outputs = [1:]
def main():

    configSetup()


if __name__ == "__main__":
    pass
