#!/usr/bin/python3
import argparse
import signal
import essentials_cubanman_server as server
import essentials_cubanman_client as client

#functions

def whichEnc(args:dict) -> int:

    if args.tls: return 1
    if args.tls1v1: return 2
    if args.tls1v2: return 3
    return 0

def ifProxy(args:dict) -> None:
    if args.proxy:
        args.static = True
        if args.buffsize < 1024:
            args.buffsize = 1024

def ifStls(args:dict) -> None:
    if args.stls:
        args.verify_ca = True
        args.verify_hostname = True
        args.tls = True

def set_server(args):

    ifProxy(args)

    if args.debug : print(f'ARGUMENTS: {args}')

    cubanman = server.Sock(args.interface[0], int(args.port), int(args.client_count), args.format, int(args.buffsize), args.static, whichEnc(args), args.tls_chain, args.tls_bundle, args.tls_key, args.proxy, args.debug)
    stdin = server.Input()
    processes = server.Processes([cubanman, stdin], args.debug)

    signal.signal(signal.SIGINT, processes.close)
    cubanman.listen()
    processes.start()

def set_client(args):

    ifStls(args)
    
    if args.debug : print(f'ARGUMENTS: {args}')
    
    cubanman = client.Sock(args.interface[0], int(args.port), args.format, int(args.buffsize), args.static, whichEnc(args), args.verify_hostname, args.verify_ca, args.tls_bundle, args.hostname, args.debug)
    stdin = client.Input()
    processes = client.Processes([cubanman, stdin], args.debug)

    signal.signal(signal.SIGINT, processes.close)
    cubanman.connect()
    processes.start()

def parse() -> dict:

    parser = argparse.ArgumentParser(
            description='cubanman creates a connection between two computers (at least), either by listening for connections, or connecting to a listening machine')

    parser.add_argument('interface', nargs=1, help='Define an address', type=str)

    parser.add_argument('-p', '--port', nargs='?', help='Define a port. The default is 15000', type=int, default=8888)

    parser.add_argument('-l', '--listen', help='Listening mode', action='store_true')

    parser.add_argument('--proxy', action='store_true', help='HTTP proxy mode')

    parser.add_argument('-d', '--debug', action='store_true', help='Show debug output.')

    parser.add_argument('-bs', '--buffsize', nargs='?', type=int, default=12, help="Define the buffsize to be used when sending and receiving data")

    parser.add_argument('-f', '--format', nargs='?', type=str, default='utf-8', help='Format to be used when encoding strings. example: utf-8')

    parser.add_argument('-cn', '--client-count', nargs='?', type=int, help='Define the client-socket limit. The default is 1', default=1)

    parser.add_argument('-stc' , '--static', action='store_true', help='Define buffer mode (static // fixed:default)')

    parser.add_argument('--tls', action='store_true', dest='tls', help='Use tls encryption')

    parser.add_argument('--tls1.1', action='store_true', dest='tls1v1', help='Use tls1.1 encryption')

    parser.add_argument('--tls1.2', action='store_true', dest='tls1v2', help='Use tls1.2 encryption')

    parser.add_argument('--tls-bundle', nargs='?', help='Specify CA bundle to be used when verifying the server CA chain', default='./certificates/cubanman.cert.pem')

    parser.add_argument('--tls-chain', nargs='?', help='Specify CA chain to be used when listening', default='./certificates/cubanman.cert.pem')

    parser.add_argument('--tls-key', nargs='?', help='Specify private key to be used when listening', default='./certificates/cubanman.key.pem')

    parser.add_argument('--verify-hostname', action='store_true', help="Check the name of the host against the cert's. ONLY use in combination with --verify-ca; alternatively use -fv or --fully-verify")

    parser.add_argument('--verify-ca', action='store_true', help="Verify the host's certificate against the ca-bundle")

    parser.add_argument('--stls', action='store_true', help="ONLY use as client. stls, short for secure tls, enables tls communications and full verification (ca-chain and hostname)")

    parser.add_argument('--hostname', nargs='?', default=None, help='Specify the hostname of the server. ONLY as a client')

    args = parser.parse_args()

    return args

#Start

def main():

    args = parse()


    #Magic

    if args.listen or args.proxy: set_server(args)
    else: set_client(args)

if __name__ == '__main__':
    main()
