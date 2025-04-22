#!/usr/bin/python3
import socket
import select
import sys
import utils_cubanman as utils

class Sock():
    
    def __init__(self, addr:str, port:int, client_count:int, enc_format:str, buffsize:int, static_mode:bool, debug:bool = False):

        self.addr = addr
        self.port = port
        self.client_count = client_count
        self.enc_format = enc_format
        self.buffsize = buffsize
        self.static_mode = static_mode
        self.debug = debug
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

    def listen(self) -> None:

        try:
            self.sock.bind((self.addr, self.port))
            if self.debug: print(f'[SERVER] socket was bound to {self.addr} {self.port}')

        except OSError:
            print('Conflict when binding address to socket. Maybe address is already being used')
            sys.exit(1)

        self.sock.listen(self.client_count)
        if self.debug: print('[SERVER] listening for connections')

    def fileno(self) -> int:
        return self.sock.fileno()

    def accept(self) -> socket.socket:
        conn_sock, details = self.sock.accept()
        if self.debug: print(f'[SERVER] connection accepted {details}')
        del details
        return conn_sock

    def broadcasting(self, instances:list, msg:str) -> None:

        msgout, msgoutlen = utils.padding(msg, self.enc_format, self.buffsize)
        
        for instance in instances:
            if instance == self or instance == instances[0]: continue

            instance.send(msgoutlen)
            instance.send(msgout)
            if self.debug: print(f'[SERVER] message: "{msg}", was sent')
    
    def recv(self, conn:socket.socket, instances:list) -> bool:

        msg_len = conn.recv(self.buffsize).decode(self.enc_format)
        if not msg_len:
            if self.debug: print('[SERVER] a client has disconnected')
            return False

        if not self.static_mode:

            try:
                msg = conn.recv(int(msg_len)).decode(self.enc_format)
            except ValueError:
                print('[SERVER] client does not seem to be using static buffer mode. Client will be notified and disconnected')
                conn.send('from [SERVER] -> Client be disconnected due to a buffer mode incompatibility'.encode(self.enc_format))
                conn.close()
                return False

            self.broadcasting(instances, msg)
            print(msg)
            return True

        self.broadcasting(instances, msg_len)
        print(msg_len)
        return True

    def close(self, *args) -> None:
        self.sock.close()
        print('[SERVER] keyboard interrupt detected. Ending...')
        sys.exit(0)

class Input():

    def __init__(self):
        pass

    @staticmethod
    def fileno() -> int:
        return sys.stdin.fileno()

    @staticmethod
    def readline() -> str:
        return sys.stdin.readline().strip()

def main_loop(instances:list) -> None:

    while True:

        ready, _, _ = select.select(instances, [], [])

        for instance in ready:

            if instance == instances[1]:
                instances.append(instances[1].accept())

            elif instance == instances[0]:
                
                if len(instances) != 2:
                    msg = instances[0].readline()
                    instances[1].broadcasting(instances, msg)

                else: print(f'unable to send "{stdin_reader.readline()}". No connections yet...')

            else:
                if instances[1].recv(instance, instances) == False:
                    instances.remove(instance)
