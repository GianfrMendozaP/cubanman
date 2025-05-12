#!/usr/bin/python3
import sys
import argparse
import signal
import essentials_cubanman_server as server

#functions

def start_server(args):

    def whichEnc(args:dict) -> int:

        if args.tls: return 1
        if args.tls1v1: return 2
        if args.tls1v2: return 3

        return 0


    #Start listening
    cubanman = server.Sock(args.interface[0], int(args.port), int(args.client_count), args.format, int(args.buffsize), args.static, whichEnc(args) , args.debug)

    stdin = server.Input()
    processes = server.Processes([cubanman, stdin], args.debug)

    signal.signal(signal.SIGINT, processes.close)
    cubanman.listen()
    processes.start()

def parse() -> dict:

    parser = argparse.ArgumentParser(
            description='cubanman creates a connection between two computers (at least), either by listening for connections, or connecting to a listening machine')

    parser.add_argument('interface', nargs=1, help='Define an address', type=str)

    parser.add_argument('-p', '--port', nargs='?', help='Define a port. The default is 15000', type=int, default=15000)

    parser.add_argument('-l', '--listen', help='Listening mode', action='store_true')

    parser.add_argument('-d', '--debug', action='store_true', help='Show debug output.')

    parser.add_argument('-bs', '--buffsize', nargs='?', type=int, default=12, help="Define the buffsize to be used when sending and receiving data")

    parser.add_argument('-stc' , '--static', action='store_true', help='Define buffer mode (static // fixed:default)')

    parser.add_argument('--tls', action='store_true', dest='tls', help='Use tls encryption')

    parser.add_argument('--tls1.1', action='store_true', dest='tls1v1', help='Use tls1.1 encryption')

    parser.add_argument('--tls1.2', action='store_true', dest='tls1v2', help='Use tls1.2 encryption')

    parser.add_argument('-f', '--format', nargs='?', type=str, default='utf-8', help='Format to be used when encoding strings. example: utf-8')

    parser.add_argument('-cn', '--client-count', nargs='?', type=int, help='Define the client-socket limit. The default is 1', default=1)    


    args = parser.parse_args()

    if args.debug : print(f'ARGUMENTS: {args}')

    return args

#Start

def main():

    args = parse()

    #Magic

    if args.listen: start_server(args)

if __name__ == '__main__':
    main()
