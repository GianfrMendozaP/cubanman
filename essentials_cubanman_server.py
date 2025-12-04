#!/usr/bin/python3
import socket
import ssl
import select
import sys
import utils_cubanman_base as utils
class Sock():
    
    def __init__(self, logger, addr:str, port:int, client_count:int, enc_format:str, buffsize:int, static_mode:bool, encryption:int=0, ca_chain:str=None, ca_bundle:str=None, ca_key:str=None):

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
        self.context = None
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.logger = logger

        if self.encryption != 0: self.encrypt()

    def __str__(self) -> str:
        attrs = ''
        for key, value in vars(self).items():
            attrs += f'{key}: {value}\n'

        return attrs

    @staticmethod
    def settimeout(conn, value) -> None:
        conn.settimeout(value)

    def fileno(self) -> int:
        return self.sock.fileno()

    def close(self) -> None:
        self.sock.close()

    def encrypt(self):

        self.logger.cubanman.info('setting up ssl/tls layer')

        match self.encryption:

            case 1:self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            case 2:self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_1_SERVER)
            case 3:self.context = ssl.SSLContext(ssl.PROTOCOL_TLS1_2_SERVER)

        self.logger.cubanman.info('loading ca-chain and private key')
        self.context.load_cert_chain(certfile=self.ca_chain, keyfile=self.ca_key)

    def listen(self) -> None:

        try:
            self.logger.cubanman.info(f'binding server to {self.addr} {self.port}')
            self.sock.bind((self.addr, self.port))

        except OSError:
            self.logger.cubanman.error('conflict when binding address to socket. Maybe address is already being used')
            sys.exit(1)


        self.logger.cubanman.info('server is listening for connections')
        self.sock.listen(self.client_count)

    def accept(self) -> socket.socket:
        self.logger.cubanman.info('a new connection was received')
        conn_sock, details = self.sock.accept()
        self.logger.cubanman.debug(f'connection: {conn_sock}:{details}')

        if self.encryption != 0:
            self.logger.cubanman.debug('wrapping connection with ssl/tls encryption')
            try: conn_sock = self.context.wrap_socket(conn_sock, server_side=True)
            except ssl.SSLError as e:
                self.logger.cubanman.warning(f'unable to stablish ssl/tls tunnel with connection')
                self.logger.cubanman.debug(f'cubanman: {e}')
                return None

            self.logger.cubanman.debug('ssl/tls layer is set')
        self.logger.cubanman.info('connection stablished')
        del details
        
        self.logger.cubanman.debug('setting timeout on socket')
        self.settimeout(conn_sock, 10)

        return conn_sock

    def broadcasting(self, instances:list, msg:str, exception:socket.socket=None) -> None:

        self.logger.cubanman.debug('getting data and datalen to broadcast')
        msgout, msgoutlen = utils.padding(msg, self.enc_format, self.buffsize)
        
        for instance in instances:
            if instance == self or isinstance(instance, Input) or instance == exception: continue

            if not self.static_mode: instance.send(msgoutlen)

            instance.send(msgout)

        self.logger.cubanman.debug(f'message: "{msg}" /\/\/\ was broadcast\nException: {exception}')
    
    def recv(self, conn:socket.socket, instances:list) -> bool:

        self.logger.cubanman.debug('server is receiving data')
        data = conn.recv(self.buffsize)

        if not data:
            self.logger.cubanman.info('a connection was closed')
            self.logger.cubanman.debug(f'connection: {conn}')
            return False

        data = data.decode(self.enc_format)

        if not self.static_mode:
            self.logger.cubanman.debug(f'data: {data}')

            try:
                data = conn.recv(int(data)).decode(self.enc_format)
            except ValueError:
                self.logger.cubanman.warning('connection does not seem to be using static buffer mode. connection will be notified and closed')
                self.logger.cubanman.debug(f'connection: {conn}')
                conn.send('from [SERVER]: connection will be closed due to a buffer mode incompatibility'.encode(self.enc_format))
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

    def __init__(self, logger, instances:list) -> None:

        self.instances = instances
        self.logger = logger

    def linker(self):
        for instance in self.instances:
            if isinstance(instance, Sock):
                self.logger.cubanman.debug('reference to Sock was found')
                setattr(self, 'server', instance)
            elif isinstance(instance, Input): 
                self.logger.cubanman.debug('reference to Input was found')
                setattr(self, 'stdin', instance)

    def start(self) -> None:

        self.linker()

        self.logger.cubanman.info('starting to listen')

        while True:

            ready, _, _ = select.select(self.instances, [], [])

            for instance in ready:

                if instance == self.server:
                    conn = self.server.accept()
                    
                    match conn:
                        case None: continue
                        case False: self.close()
                        case _: self.instances.append(conn)

                elif instance == self.stdin:
                    msg = self.stdin.readline()
                    self.server.broadcasting(self.instances, msg)

                else:
                    if self.server.recv(instance, self.instances) == False:
                        self.instances.remove(instance)

    
    def close(self, *args):
        print('\nkeyboard interrupt received, ending ...')
        self.logger.cubanman.debug('SIGINT signal was received. Ending')
        
        for instance in self.instances:
            instance.close()

        self.logger.cubanman.debug('stopping queue listener')
        self.logger.stopListener()
        sys.exit(0)
