#!/usr/bin/python3
import socket
import select
import sys
import utils_cubanman as utils

class Sock():
    
    def __init__(self, addr:str, port:int, client_count:int, enc_format:str, buffsize:int, static_mode:bool):

        self.addr = addr
        self.port = port
        self.client_count = client_count
        self.enc_format = enc_format
        self.buffsize = buffsize
        self.static_mode = static_mode
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

    def listen(self) -> None:

        try:
            self.sock.bind((addr,port))

        except OSError:
            print('Conflict when binding address to socket. Maybe address is already being used')
            sys.exit(1)

        self.sock.listen()

    def fileno(self) -> int:
        return self.sock.fileno()

    def accept(self) -> socket.socket:
        conn_sock, _ = self.sock.accept()
        return conn_sock

    def broadcasting(self, socks:list, msg:str) -> None:

        msgout, msgoutlen = utils.padding(msg, self.enc_format)
        
        for conn in socks:
            if conn == self.sock: continue

            conn.send(msgoutlen)
            conn.send(msgout)
    
    def recv(self, conn:socket.socket, socks:list) -> bool:

        msg_len = int(conn.recv(self.buffsize).decode(self.enc_format))
        if not msg_len: return False

        if not self.static_mode:
            msg = conn.recv(msg_len).decode(self.enc_format)
            self.broadcasting(socks, msg)
            print(msg)
            return True

        else:
            self.broadcasting(socks, msg_len)
            print(msg_len)
            return True

    def close(self, *args) -> bool:
        self.sock.close()
        sys.exit(0)

class Input():

    def __init__(self):
        pass

    @staticmethod
    def fileno() -> int:
        return sys.stdin.fileno()

    @staticmethod
    def readline() -> str:
        return sys.stdin.readline()

def main_loop(socks:list, stdin_reader:Input) -> None:

    while True:

        ready, _, _ = select.select([socks, stdin_reader], [], [])

        for instance in ready:

            if instance == socks[0].sock:
                socks.append(socks[0].accept())

            elif instance == sys.stdin:
                msg = sys.stdin.readline()
                socks[0].broadcasting(socks, msg)

            else:
                if socks[0].recv(instance) == False:
                    socks.remove(instance)
