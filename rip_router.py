import sys
import re
import socket

def config_read():

    if len(sys.argv) != 2:
        print("Please only give me one argument!")

    router_id, input_ports, outputs = None, None, None
    file_name = sys.argv[1]

    with open(file_name) as file:
        for line in file:
            line = re.split(', | ', line)
            print(line)
            if line[0] == '//' or line[0] == '\n':
                continue
            elif line[0] == "router-id":
                router_id = line[1]
            elif line[0] == "input-ports":
                input_ports = line[1:]
            elif line[0] == "outputs":
                outputs = line[1:]
            else:

    print(router_id)
    print(input_ports)
    print(outputs)

def router_setup(router_id, input_ports, outputs):
    pass

def main():

    config_read()
    router_setup()

if __name__ == "__main__":
    main()
