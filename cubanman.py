#!/usr/bin/python3

import socket
import argparse
import sys
import threading
import signal
import select

#Socket Class

class sock:

    def __init__(self, sock, ft, buffsize, debug):

        self.clients = []
        self.threads = []
        self.ft = ft
        self.buffsize = buffsize
        self.debug = debug
        self.flag = threading.Event()
        self.close_signal = '$<-EXIT->$'.encode(ft)

        if sock == None:
            if self.debug: print('-CREATING socket: family AF_INET type SOCK_STREAM')
            self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        else:
            self.sock = sock

    #Server socket listening function
    def listen(self, address:str, port:int, clinum:int) -> None:
        
        try: self.sock.bind((address, int(port)))

        except OSError as e: 
            
            print(f'-ERROR in -> cubanman/listen: {address} {port} already in use')
            self.sock.close()
            sys.exit(1)

        setattr(self, 'addr', (address, int(port)))
        self.sock.listen(int(clinum+1))

        #helper
        self.threads.append(threading.Thread(target=self.closing_helper, args=[self.flag]))
        self.threads[-1].start()
        #broadcasting
        self.threads.append(threading.Thread(target=self.server_handler, daemon=True))
        self.threads[-1].start()
        #recv
        self.threads.append(threading.Thread(target=self.recv, daemon=True))
        


        while True:

            try:

                addr, port = self.sock.accept()

            except OSError:
                if self.debug: print(f'-cubanman/listen: bad file descriptor, maybe this socket was closed?')

            self.clients.append(addr)
            if self.debug: print(f'-[SERVER] CONNECTION from {self.clients[-1]} clients: {len(self.clients) -1}')
            
            #It's necessary to find a way to update recv() when a client is added
            if self.threads[-1].is_alive() == False and len(self.clients) == 2:
                self.threads[-1].start()

        

    #Later on
    def command_execution(self, stdin:str) -> None:
        pass

    #Server socket client handler function
    def server_handler(self) -> None:
        
        while True:   
                
            msg = input('')

            if self.flag.is_set(): break

            self.broadcasting(msg)

        if self.debug: print('-cubanman/server_handler: ENDING thread')


    #Send to all clients:
    def broadcasting(self, msg:str, exclude:object = None) -> None:

        if len(self.clients) != 1:

            if self.buffsize > 64: msgout, msgoutlen = self.padding(msg)

            for client in self.clients:

                if client == exclude: continue

                if self.buffsize > 64: client.send(f'{msg}\n'.encode(self.ft))

                else:
                    if client.send(msgoutlen) != 0:
                        client.send(msgout)

                    else:
                        print('cubanman/server_handler: Maybe client disconencted?')



    #Server side receive function
    def recv(self) -> None:

        if self.debug: print('- cubanman/recv: RECEIVING data')
        
        while True:

            try: 
                clients, _, _ = select.select(self.clients, [], [], 1)

                for c in clients:

                    length = c.recv(self.buffsize).decode(self.ft)

                    if not length: self.clients.remove(c)
                    
                    else:
                    
                        if length == self.close_signal.decode(self.ft):
                            if self.debug: print('- cubanman/recv: closing signal received. The loop will be broken')
                            break

                        if self.buffsize > 64:
                            print(length, end='')
                            self.broadcasting(length, c)
                        else: print(c.recv(int(length)).decode(self.ft), end='')

            except ConnectionResetError as e:
                if self.debug: print(f'- cubanman/recv: Expected error: {e}')
                break

            if self.flag.is_set(): break
            

        if self.debug: print('-cubanman/recv: CLOSING thread')

    #Padding function for sending messages
    def padding(self, msg:str) -> tuple:

        stdin = f'{msg}\n'.encode(self.ft)

        stdinlen = f'c{len(stdin)}'.encode(self.ft)

        stdinlen = stdinlen + (b' ' * (self.buffsize - len(stdinlen)))
        return(stdin, stdinlen)


    def close(self, *kargs) -> None:
        print('keyboard interrupt received. Ending :)')

        #Setting flag to true
        self.flag.set()

        if self.debug: print('- cubanman/close: The flag was set') 


        if self.debug: 
            print('- threads:',threading.active_count())
            print('- cubanman/close: joining recv thread')

       #Joining all threads
        for i,t in enumerate(reversed(self.threads)):
            
            if i == 1: print('press enter to finish')
            t.join()

        if self.debug:
            print('- cubanman/close: all threads were joint :)')
            print(threading.active_count())


        #Disconnecting all clients
        for c in self.clients:
            c.close()
            if self.debug: print(f'- cubanman/close: {c} was disconnected')

        #Closing server socket
        self.sock.close()

        sys.exit(0)

    def closing_helper(self, flag) -> None:
        
        helper = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

        helper.settimeout(10)

        try: helper.connect(self.addr)
        except socket.timeout as e: sys.exit(1)
        flag.wait()
        helper.send(self.close_signal)


#Start

def main():

    # - - - Parser - - -

    #basics
    parser = argparse.ArgumentParser(
            description='cubanman creates a connection between two computers (at least), either by listening for connections, or connecting to a listening machine', epilog='The program is structured as follows: main options: -d,-bs,-f,-cn; these will partially configure the behavior of cubanman; and then come the functions: listen, connect, etc.Example: cubanman.py -d -f utf-8 -cn 2 listen 127.0.0.1 26554')


    parser.add_argument('-d', '--debug', action='store_true', help='show debug output.')

    parser.add_argument('-bs', '--buffsize', nargs='?', type=int, default=12, help="defines the buffsize to be used when sending and receiving data. After, the message is defined, a variable saves the message length and is padded in order to meet the buffersize, thus, the receiver will receive the data (length of the message), then use that as the new buffsize, and finally receiving the actual message. If buffsize happens to be a number higher than 64, a static-like receiving method will be used, this means no length will be received, just a fixed byte-length that will determine a big/short the data will be.")

    parser.add_argument('-f', '--format', nargs='?', type=str, default='utf-8', help='format to be used when encoding strings. example: utf-8')

    parser.add_argument('-cn', '--client-number', nargs='?', type=int, help='defines the number of clients the socket server can host. The default value is 1', default=1)

    subparsers = parser.add_subparsers(title='subcommands')
    
    #listening mode

    listening_mode = subparsers.add_parser('listen', help='listen <Ipv4> <port>')

    listening_mode.add_argument('-b', '--bind', nargs='?', default='0.0.0.0', help='-b/--bind <Ipv4>')
    
    listening_mode.add_argument('-p', '--port', nargs='?', default=15000, help='-p/--port <port>')

    #connecting mode

    connecting_mode = subparsers.add_parser('connect', help='connect <Ipv4> <port>')

    connecting_mode.add_argument('Ipv4', nargs=1, type=str, help='Ipv4 to connect to')
    connecting_mode.add_argument('port', nargs=1, type=int, help='port to connect to')


    args = parser.parse_args()

    if args.debug : print(f'ARGUMENTS: {args}')


    #Magic

    cubanman = sock(sock=None,ft=args.format, buffsize=args.buffsize, debug=args.debug)


    signal.signal(signal.SIGINT, cubanman.close)

    if hasattr(args, 'bind'):

        cubanman.listen(args.bind, args.port, args.client_number)



if __name__ == '__main__':
    main()
