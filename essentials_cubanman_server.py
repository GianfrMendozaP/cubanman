#!/usr/bin/python3
import socket
import ssl
import select
import sys
import utils_cubanman as utils

class Sock():
    
    def __init__(self, addr:str, port:int, client_count:int, enc_format:str, buffsize:int, static_mode:bool, encryption:int=0, ca_chain:str=None, ca_bundle:str=None, ca_key:str=None, debug:bool=False):

        self.addr = addr
        self.port = port
        self.client_count = client_count
        self.enc_format = enc_format
        self.buffsize = buffsize
        self.static_mode = static_mode
        self.encryption = encryption
        self.ca_chain = ca_chain
        self.ca_bundle = ca_bundle
        self.ca_key = ca_key
        self.debug = debug
        self.context = None
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

        if self.encryption != 0: self.encrypt()

    @staticmethod
    def settimeout(conn, value) -> None:
        conn.settimeout(value)

    def fileno(self) -> int:
        return self.sock.fileno()

    def close(self) -> None:
        self.sock.close()

    def encrypt(self):

        match self.encryption:

            case 1:self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            case 2:self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_1_SERVER)
            case 3:self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_2_SERVER)

        self.context.load_cert_chain(certfile=self.ca_chain, keyfile=self.ca_key)

    def listen(self) -> None:

        try:
            self.sock.bind((self.addr, self.port))
            if self.debug: print(f'[SERVER] |BINDING| socket was bound to {self.addr} {self.port}')

        except OSError:
            print('[SERVER] |ERROR| Conflict when binding address to socket. Maybe address is already being used')
            sys.exit(1)

        self.sock.listen(self.client_count)
        if self.debug: print('[SERVER] |LISTENING| listening for connections')

    def accept(self) -> socket.socket:
        conn_sock, details = self.sock.accept()

        if self.encryption != 0:
            try: conn_sock = self.context.wrap_socket(conn_sock, server_side=True)
            except ssl.SSLError as e:
                print(f'[SERVER] |ERROR| Unable to stablish connection with {details}')
                if self.debug: print(f'cubanman: {e}')
                return None

            if self.debug: print('[SERVER] |SSL| SSL-layer was set')
        if self.debug: print(f'[SERVER] |CONNECTION| connection accepted {details}')
        del details

        self.settimeout(conn_sock, 10)

        return conn_sock

    def broadcasting(self, instances:list, msg:str, exception:socket.socket=None) -> None:

        msgout, msgoutlen = utils.padding(msg, self.enc_format, self.buffsize)
        
        for instance in instances:
            if instance == self or isinstance(instance, Input) or instance == exception: continue

            if not self.static_mode: instance.send(msgoutlen)

            instance.send(msgout)

        if self.debug: print(f'[SERVER] message: "{msg}", was broadcast')
    
    def recv(self, conn:socket.socket, instances:list) -> bool:

        data = conn.recv(self.buffsize)

        if not data:
            if self.debug: print('[SERVER] |DISCONNECTION| a client has disconnected')
            return False

        data = data.decode(self.enc_format)

        if not self.static_mode:

            try:
                data = conn.recv(int(data)).decode(self.enc_format)
            except ValueError:
                print('[SERVER] |ERROR| client does not seem to be using static buffer mode. Client will be notified and disconnected')
                conn.send('from [SERVER] -> Client will be disconnected due to a buffer mode incompatibility'.encode(self.enc_format))
                conn.close()
                return False

        print(data)

        self.broadcasting(instances, data, conn)
        return True

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

class Processes:

    def __init__(self, instances:list, debug:bool=False) -> None:

        self.instances = instances
        self.debug = debug

    def linker(self):

        for instance in self.instances:
            if isinstance(instance, Sock):
                if self.debug: print('[PROCESSES] reference to Sock was found')
                setattr(self, 'server', instance)
            elif isinstance(instance, Input): 
                if self.debug: print('[PROCESSES] reference to Input was found')
                setattr(self, 'stdin', instance)

    def start(self) -> None:

        self.linker()

        if self.debug: print('[PROCESSES] starting main loop')

        while True:

            ready, _, _ = select.select(self.instances, [], [])

            for instance in ready:

                if instance == self.server:
                    conn = self.server.accept()
                    
                    match conn:
                        case None: continue
                        case _: self.instances.append(conn)

                elif instance == self.stdin:
                    msg = self.stdin.readline()
                    self.server.broadcasting(self.instances, msg)

                else:
                    if self.server.recv(instance, self.instances) == False:
                        self.instances.remove(instance)

    
    def close(self, *args):
        print('\nkeyboard interrupt received, ending ...')
        
        for instance in self.instances:
            instance.close()

        sys.exit(0)
