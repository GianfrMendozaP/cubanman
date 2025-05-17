#!/usr/bin/python3

import utils_cubanman.py as utils
import socket
import select
import ssl
import sys

class Sock():

    def __init__(self, addr:str, port:int, enc_format:str, buffsize:int, static_mode:bool, encryption:int=0, ca_bundle:str, debug:bool=False ):

        self.addr = addr
        self.port = port
        self.enc_format = enc_format
        self.buffsize = buffsize
        self.static_mode = static_mode
        self.encryption = encryption
        self.ca_bundle = ca_bundle
        self.debug = debug
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

    def encrypt(self) -> None:

        ###### READ DOCUMENTATION TO KNOW HOW TO LOAD CA BUNDLES (FEATURE HASN'T BEEN ADDED)

        setattr(self, 'context', None)

        match self.encryption:
            
            case 1:
                self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            case 2:
                self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_1_CLIENT)
            case 3:
                self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_2_CLIENT)

        self.context.load_cert_ca_bundle(cafile=self.ca_bundle)

    def connect(self) -> None:

        if self.debug: print(f'[CLIENT] connecting to {self.addr}, {self.port}')

        try:
            self.sock.connect((self.addr, self.port))
        except OSError as e:
            print(f'[CLIENT] unable to connect to {self.addr}, {self.port}')
            if self.debug: print(f'cubanman: {e}')
            sys.exit(1)

    def fileno(self) -> None:
        return self.sock.fileno()

    def recv(self) -> None:
        
        data = self.sock.recv(buffsize).decode(self.enc_format)
        
        if not self.static_mode:
        
            try: data = self.sock.recv(int(data)).decode(self.enc_format)
            except ValueError:
                print('Incorrect buffer mode, maybe... Exiting')
                self.close()
                sys.exit(1)

        print(data)

    def send(self, data:str) -> None:
    
        if not static_mode:
            data, datalen = utils.padding(data, self.enc_format, self.buffsize)
            if self.sock.send(datalen) == 0:
                if self.debug: print('[CLIENT] unable to send data. Maybe host is down... Exiting')
                self.close()
                sys.exit(1)
            self.sock.send(data)
        else:
            if self.sock.send(data.encode(self.enc_format)) == 0: 
                if self.debug: print('[CLIENT] unable to send data. Maybe host is down... Exiting')
                self.close()
                sys.exit(1)

    def close(self):
        self.sock.close()

class Input():

    def __init__(self):
        pass

    @staticmethod
    def fileno() -> int:
        return sys.stdin.fileno()

    @staticmethod
    def readline() -> str:
        return sys.stdin.readline().strip()

    @staticmethod
    def close() -> None:
        return None

class Processes():

    def __init__(self, instances:list, debug:bool=False) -> None:

        self.instances = instances
        self.debug = debug

def linker(self):

    for instance in self.instances:

        if isinstance(instance, Sock):
            if self.debug: print('[PROCESSES] reference to Sock was found')
            setattr(self, 'sock', instance)

        elif isinstance(instance, Input):
            if self.debug: print('[PROCESSES] reference to Input was found')
            setattr(self, 'input', instance)

    def start(self):

        while True:

            ready, _, _ = select.select(self.instances, [], [])

            for instance in ready:
                
                if instance == self.sock:
                    self.sock.recv()

                elif instance == self.input:
                    self.sock.send(self.input.readline())

    def close(self, *args)

        print('\nkeyboard interrupt received... Exiting')

        for instance in self.instances:
            instance.close()

        sys.exit(0)
