#!/usr/bin/python3

import utils_cubanman as utils
import socket
import select
import ssl
import sys

class Sock():

    def __init__(self, addr:str, port:int, enc_format:str, buffsize:int, static_mode:bool, encryption:int=0, verify_hostname:bool=False, verify_ca:bool=False, ca_bundle:str=None, hostname:str=None,debug:bool=False ):

        self.addr = addr
        self.port = port
        self.enc_format = enc_format
        self.buffsize = buffsize
        self.static_mode = static_mode
        self.encryption = encryption
        self.verify_hostname = verify_hostname
        self.verify_ca = verify_ca
        self.ca_bundle = ca_bundle
        self.hostname = hostname
        self.debug = debug
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)


        if self.encryption != 0: self.encrypt()

    def encrypt(self) -> None: 

        if self.debug: print('[CLIENT] creating encryption context...')

        setattr(self, 'context', None)

        match self.encryption:
            case 1: self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            case 2: self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_1_CLIENT)
            case 3: self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_2_CLIENT)
    
        self.check_CA()
        self.check_hostname()

    def check_CA(self):

        if self.verify_ca:

            if self.debug: print('[CLIENT] loading ca-file...')
            self.context.load_verify_locations(cafile=self.ca_bundle)
            self.context.verify_mode = ssl.CERT_REQUIRED

            if self.verify_hostname:
                if self.debug: print('[CLIENT] setting check hostname to true...')
                self.context.check_hostname = True
            else:
                if self.debug: print('[CLIENT] setting check hostname to false...')
                self.context.check_hostname = False

        else:
            print('[CLIENT] setting insecure context for connection...')
            self.context.check_hostname = False
            self.context.verify_mode = ssl.CERT_NONE

    def check_hostname(self):

        #AS AN EXTRA OPTION, A CUSTOM HOSTNAME MIGHT AS WELL BE PROVIDED
        if self.hostname != None:
            if self.debug: print(f'[CLIENT] hostname was defined as {self.hostname}...')
            self.sock = self.context.wrap_socket(self.sock, server_hostname=self.hostname)
        else: 
            if self.debug: print('[CLIENT] no hostname was defined...')
            self.sock = self.context.wrap_socket(self.sock, server_hostname=self.addr)

    def connect(self) -> None:

        if self.debug: print(f'[CLIENT] connecting to {self.addr}:{self.port}')

        try:
            self.sock.connect((self.addr, self.port))
        except Exception as e:
            print(f'[CLIENT] unable to connect to {self.addr}:{self.port}')
            if self.debug: print(f'cubanman: {e}')
            sys.exit(1)

        #IN ORDER TO AVOID UNDESIRED RECV() CALLS
        self.sock.setblocking(False)

    def fileno(self) -> int:
        return self.sock.fileno()

    def recv(self) -> None:

        if self.debug: print('[CLIENT] receiving data...')
        
        try:
            data = self.sock.recv(self.buffsize).decode(self.enc_format)
        except ssl.SSLWantReadError:
            if self.debug: print('[CLIENT] SSLWantReadError was caugth and will be ignored...')
            return None

        if not data:
            print('[CLIENT] host went offline, maybe... Exiting')
            self.close()
            sys.exit(0)

        if not self.static_mode:
        
            try: data = self.sock.recv(int(data)).decode(self.enc_format)
            except ValueError:
                print('Incorrect buffer mode, maybe... Exiting')
                self.close()
                sys.exit(0)

        print(data)

    def send(self, data:str) -> None:
        if self.debug: print('[CLIENT] sending data...')
    
        if not self.static_mode:
            data, datalen = utils.padding(data, self.enc_format, self.buffsize)
            if self.sock.send(datalen) == 0:
                if self.debug: print('[CLIENT] unable to send data. Maybe host is down... Exiting')
                self.close()
                sys.exit(0)
            self.sock.send(data)
        else:
            if self.sock.send(data.encode(self.enc_format)) == 0: 
                if self.debug: print('[CLIENT] unable to send data. Maybe host is down... Exiting')
                self.close()
                sys.exit(0)

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

        self.linker()

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

    def close(self, *args):

        print('\nkeyboard interrupt received... Exiting')

        for instance in self.instances:
            instance.close()

        sys.exit(0)
