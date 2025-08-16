#!/usr/bin/python3

import utils_cubanman_base as utils
import socket
import select
import ssl
import sys

class Sock():

    def __init__(self, logger, addr:str, port:int, enc_format:str, buffsize:int, static_mode:bool, encryption:int=0, verify_hostname:bool=False, verify_ca:bool=False, ca_bundle:str=None, hostname:str=None):

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
        self.logger = logger
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)


        if self.encryption != 0: self.encrypt()

    def encrypt(self) -> None: 

        self.logger.cubanman.info('setting ssl/tls layer')

        setattr(self, 'context', None)
        self.logger.cubanman.debug(f'encrption: {self.encryption}')
        match self.encryption:
            case 1: self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            case 2: self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_1_CLIENT)
            case 3: self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_2_CLIENT)
    
        self.check_CA()
        self.check_hostname()

    def check_CA(self):

        if self.verify_ca:

            self.logger.cubanman.info('loading ca-file...')
            self.context.load_verify_locations(cafile=self.ca_bundle)
            self.context.verify_mode = ssl.CERT_REQUIRED

            if self.verify_hostname:
                self.logger.cubanman.debug('setting check hostname to true...')
                self.context.check_hostname = True
            else:
                self.logger.cubanman.debug('setting check hostname to false...')
                self.context.check_hostname = False

        else:
            self.logger.cubanman.debug('[CLIENT] setting insecure context for connection...')
            self.context.check_hostname = False
            self.context.verify_mode = ssl.CERT_NONE

    def check_hostname(self):

        #AS AN EXTRA OPTION, A CUSTOM HOSTNAME MIGHT AS WELL BE PROVIDED
        if self.hostname != None:
            self.logger.cubanman.info(f'hostname was defined as {self.hostname}')
            self.sock = self.context.wrap_socket(self.sock, server_hostname=self.hostname)
        else: 
            self.logger.cubanman.info('no hostname was defined...')
            self.sock = self.context.wrap_socket(self.sock, server_hostname=self.addr)

    def connect(self) -> None:

        self.logger.cubanman.info(f'connecting to {self.addr}:{self.port}')

        try:
            self.sock.connect((self.addr, self.port))
        except Exception as e:
            self.logger.cubanman.error(f'unable to connect to {self.addr}:{self.port}')
            self.logger.cubanman.error(f'cubanman: {e}')
            sys.exit(1)

        #IN ORDER TO AVOID UNDESIRED RECV() CALLS
        self.logger.cubanman.debug('setting socket to non-blocking mode')
        self.sock.setblocking(False)

    def fileno(self) -> int:
        return self.sock.fileno()

    def recv(self):
        
        self.logger.cubanman.debug('receiving data')
        
        try:
            data = self.sock.recv(self.buffsize).decode(self.enc_format)
        except ssl.SSLWantReadError:
            self.logger.cubanman.warning('SSLWantReadError was caugth and will be ignored...')
            return None

        if not data:
            #REMINDER FOR LATER: MODIFY FUNCTION TO RETURN FALSE IN CASE HOST GOES OFFLINE, AND THEN CLOSE EVERYTHING FROM PROCESSES
            self.logger.cubanman.info('host went offline. Exiting')
            self.close()
            sys.exit(0)

        if not self.static_mode:
            
            self.logger.cubanman.debug(f'data: {data}')
        
            try: data = self.sock.recv(int(data)).decode(self.enc_format)
            except ValueError:
                #THE REMINDER APPLIES TO THIS FUNCTION TOO
                self.logger.cubanman.error('incorrect buffer mode (most likely). Exiting')
                self.close()
                sys.exit(0)

        print(data)
        self.logger.cubanman.debug(f'data: {data}')

    def send(self, data:str) -> None:
        self.logger.cubanman.info('sending data')
    
        if not self.static_mode:
            data, datalen = utils.padding(data, self.enc_format, self.buffsize)
            if self.sock.send(datalen) == 0:
                #SAME REMINDER APPLIES HERE TOO
                self.logger.cubanman.error('unable to send data. Maybe host went offline... Exiting')
                self.close()
                sys.exit(0)
            self.sock.send(data)
        else:
            if self.sock.send(data.encode(self.enc_format)) == 0: 
                self.logger.cubanman.error('unable to send data. Maybe host went offline... Exiting')
                self.close()
                sys.exit(0)

    def close(self):
        self.logger.cubanman.debug('closing socket')
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

    def __init__(self, logger, instances:list) -> None:

        self.instances = instances
        self.logger = logger

        self.linker()

    def linker(self):
        self.logger.cubanman.debug('runnning linker')

        for instance in self.instances:

            if isinstance(instance, Sock):
                self.logger.cubanman.debug('reference to Sock was found')
                setattr(self, 'sock', instance)

            elif isinstance(instance, Input):
                self.logger.cubanman.debug('reference to Input was found')
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
        self.logger.cubanman.debug('SIGINT signal was received. Exiting')

        for instance in self.instances:
            instance.close()
        
        self.logger.cubanman.debug('stopping queue listener')
        self.logger.stopListener()

        sys.exit(0)
