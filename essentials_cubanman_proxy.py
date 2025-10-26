#!/usr/bin/python3
import socket
import ssl
import select
import sys
import utils_cubanman_proxy as tools
import utils_cubanman_http_headers as http

PORTS = [443, 80, 88]
WEBSERVERS = []

#STANDARDS FOR THE LOGGING OUTPUT:
#ALL ACTIONS SHOULD BE ON CONTINUOS PRESENT. E.g: listening, connecting, closing, etc...
#UNLESS IT'S DESCRIPTIVELY NECESSARY TO USE A VERB IN PAST
#NO UPPERCASE LETTERS
#NO HYPHENS/DASHES (-) ONLY USE (_) 

class Bws_sock:

    def __init__(self, logger, sock, ref_sock=None, debug:bool=True):

        self.sock = sock
        self.ref_sock = ref_sock
        self.connection = None
        self.logger = logger
        self.debug = debug
        self.name = self.__class__.__name__
        self.https = False

    def fileno(self) -> int:
        return self.sock.fileno()

    def set_status(self, connection):
        self.logger.cubanman.debug(f'setting connection status of {self.name} {id(self.sock)} and {self.ref_sock.name} {id(self.ref_sock.sock)}')
        self.connection = connection
        self.ref_sock.connection = connection

    def recv(self, buffsize):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} receiving data')
        if self.https:
            return tools.httpsRecv(self.sock, buffsize, self.logger)

        req, connection = tools.recv(self.sock, buffsize, self.logger)
        self.set_status(connection)
        return req

    def send(self, res):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending data back')

        attemps = 2
        while True:
            try:
                bytesSent = self.sock.send(res)
                #print(bytesSent)
                break
            except BrokenPipeError:
                if attemps == 0: return False #disconnect pair
                self.logger.cubanman.warning('cubanman: BrokenPipeError was caught. Retrying...')
            except ConnectionResetError:
                self.logger.cubanman.warning('cubanman: Browser closed connection.')
                return False
            attemps -= 1

        if bytesSent == len(res):
            self.logger.cubanman.debug('success')
            return True
        if bytesSent != 0:
            return self.send(res[bytesSent:])
        return False

    def go(self, req):
        return self.ref_sock.go(req)

    def proxyIt(self, req) -> bool:
        return self.ref_sock.send(req)

    def connected(self) -> bool:
        return self.ref_sock.connected()

    def close(self):
        self.sock.close()
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} was closed...')

class Proxy_sock:

    def __init__(self, logger, sock, encryption:int, ca_bundle:str, buffsize:int=1024, ref_sock=None, debug:bool=True):

        self.sock = sock
        self.encryption = encryption
        self.bundle = ca_bundle
        self.buffsize = buffsize
        self.ref_sock = ref_sock
        self.connection = None
        self.web = None
        self.httpVersion = None
        self.https = False
        self.x16 = False
        self.logger = logger
        self.debug = debug

        self.name = self.__class__.__name__

    def fileno(self) -> int:
        return self.sock.fileno()

    def setHttpVersion(self, version):
        self.httpVersion = version
        self.logger.cubanman.info(f'protocol version was set to {version}')

    def encrypt(self, webserver):

        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} encrypting connection')

        #setattr(self, 'context', ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
        #sock = self.context.wrap_socket(self.sock, server_hostname = webserver.decode('utf-8'))
        #self.context.load_verify_locations(tools.certBundle)

        #self.sock = sock
        self.https = True
        self.ref_sock.https = True
        #self.blocking(False) #sock set to non blocking mode Has to be done after connecting
        #self.logger.cubanman.debug(f'{self.name} {id(self.sock)} encrypted connection')

    def settimeout(self,s:int):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} setting a {s} second timeout')
        self.sock.settimeout(s)

    def blocking(self, value:bool):

        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} set blocking mode to {value}')
        self.sock.setblocking(value)

    def close(self):
        self.connection = None
        self.sock.close()
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} was closed...')

    def set_status(self, connection):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} setting connection status to {connection}')
        self.connection = connection
        self.ref_sock.connection = connection

    def disassemble(self, req) -> tuple:
        return http.manage_req(req, self.debug)

    def send(self, req):
        if self.https and not self.x16: self.pastFirstx16()
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending data to {self.web}')

        attemps = 2

        while True:
            try:
                bytesSent = self.sock.send(req)
                #print(bytesSent)
                break
            except BrokenPipeError:
                if attemps == 0: return False #disconnect pair
                self.logger.cubanman.warning('cubanman: BrokenPipeError was caught. Retrying...')
            except ConnectionResetError:
                self.logger.cubanman.warning('cubanman: webserver closed connection.')
                return False
            attemps -= 1

        if bytesSent == len(req):
            self.logger.cubanman.debug('success')
            return True
        if bytesSent != 0:
            return self.send(req[bytesSent:])
        return False


    def disconnect(self):
        if self.connection == 0: return True
        return False

    def pastFirstx16(self):
        self.logger.cubanman.debug('first x16 record will be sent')
        self.x16 = True

    def connected(self):
        if self.web == None: 
            return False
        return True

    def go(self, req):
        webserver, port = self.disassemble(req)

        firstLine = http.getFirstLine(req)
        self.setHttpVersion(http.httpVersion(firstLine))

        if http.httpsType(firstLine):
            self.encrypt(webserver)
        if self.connect(webserver, port):
            self.web = webserver
            if not self.https: self.send(req)
            else: self.send_back(http.connectionResponse(self.httpVersion), self.name)
            return True
        return False

    def connect(self, webserver, port) -> bool:
        #Firewall to avoid banned webservers or ports
        if port not in PORTS or webserver in WEBSERVERS: 
            self.logger.cubanman.warning('port or webserver not safe!!!')
            return False

        try:
            self.logger.cubanman.debug(f'{self.name} {id(self.sock)} connecting to {webserver} on {port}')
            self.sock.connect((webserver, port))
            
            #if self.https:
            #    self.blocking(False)
            #else:
            self.settimeout(10)

            return True

        except OSError as e:
            self.logger.cubanman.warning(f'FAILURE cubanman: {self.name} {id(self.sock)} unable to stablish a connection with {webserver}: {e}')
            return False

        except Exception as e:
            self.logger.cubanman.warning(f'cubanman: {e}')
            return False

    def send_back(self, res, source:str='webserver'):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending back response received from {source}')
        return self.ref_sock.send(res)

    def recv(self) -> bytes:

        if self.connection == None: return b'code-0' 

        #print('receiving from', self.web)
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} receiving data from {self.web}')

        if self.https:
            if not self.x16:
                self.logger.cubanman.debug('cubanman: code-0')
                return b'code-0'
            return tools.httpsRecv(self.sock, self.buffsize, self.logger)
        
        response, connection = tools.recv(self.sock, self.buffsize, self.logger) 
        #IN ORDER TO AVOID SSLWANTREADERROR
        if connection != -1: self.set_status(connection)

        return response


class Proxy_server:
    
    def __init__(self, logger, addr:str, port:int, buffsize:int, debug:bool=True):

        self.addr = addr
        self.port = port
        self.buffsize = buffsize
        self.logger = logger
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.debug = debug

        #if self.encryption != 0: self.encrypt()

    def settimeout(self, conn, value):
        self.logger.cubanman.debug(f'proxy_server setting a {value} second timeout on sock-{id(conn)}')
        conn.settimeout(value)

    def fileno(self) -> int:
        return self.sock.fileno()

    def close(self):
        self.logger.cubanman.debug('proxy_server is closing')
        self.sock.close()

    def listen(self):

        try:
            self.logger.cubanman.info(f'binding proxy_server to {self.addr} {self.port}')
            self.sock.bind((self.addr, self.port))

        except OSError:
            self.logger.cubanman.error('cubanman: conflict when binding address to socket. Maybe address is already being used')
            sys.exit(1)
            return False
        except Exception as e:
            self.logger.cubanman.error(f'cubanman: {e}')
            return False

        self.sock.listen()
        self.logger.cubanman.info('proxy_server is listening for connections')

        return True

    def accept(self) -> socket.socket:
        conn_sock, details = self.sock.accept()
        self.logger.cubanman.debug('proxy_server accepted a connection')
        del details

        self.settimeout(conn_sock, 10) 

        proxy_sock = Proxy_sock(self.logger, socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM), 0, None, self.buffsize, None, self.debug)
        bws_sock = Bws_sock(self.logger, conn_sock, None, self.debug)

        proxy_sock.ref_sock = bws_sock
        bws_sock.ref_sock = proxy_sock

        self.logger.cubanman.debug(f'bws_sock: {id(bws_sock.sock)} | proxy_sock {id(proxy_sock.sock)}')

        return (bws_sock, proxy_sock)
    
    def recv(self, conn) -> bool:
 
        data = conn.recv(self.buffsize)

        if not data:
            self.logger.cubanman.info(f'a client has disconnected from proxy_server: sock-{id(conn)}')
            return False

        return data

class Processes:

    def __init__(self, logger, instances:list) -> None:

        self.instances = instances
        self.logger = logger

    def start(self) -> None:
        if not self.instances[0].listen(): self.close()
        self.logger.cubanman.debug('starting main loop')

        while True:

            ready, _, _ = select.select(self.instances, [], [])

            for instance in ready:

                if instance == self.instances[0]:
                    bws_client, proxy_sock = self.instances[0].accept()

                    self.instances.extend([bws_client, proxy_sock])

                else:

                    if isinstance(instance, Proxy_sock):

                        if not instance.connected(): continue

                        res = instance.recv()

                        if res == b'code-20':
                            #Indicates some type of OSError like ConnectionReset, BrokenPipe, bad FileDescriptor , etc...
                            self.delPair(instance)
                        if res == b'code-10':
                            #This indicates Timeouts that where caught because the server never sent data: data == b''
                            continue
                        if res == b'code-0':
                            #This indicates necessary omittions in case of expecting an x16 mesage or an SSLWantReadError.
                            continue
                        if res == b'code-50':
                            #This indicates that cubanman will be shutdown due to an error that needs to be checked.
                            self.close()

                        if not instance.send_back(res):
                            self.delPair(instance)

                        if instance.disconnect() or not res: 
                            self.delPair(instance)

                    else:

                        req = self.instances[0].recv(instance)
                        if req == False:
                            self.delPair(instance)
                        else:

                            #INSTEAD, JUST CHECK IF THE PROXY_SOCK.SOCK IS CONNECTED TO A WEBSERVER OR NOT
                            if not instance.connected():
                                if not instance.go(req):
                                    self.delPair(instance)
                                    continue
                            else:
                                if not instance.proxyIt(req): self.delPair(instance)

    def delPair(self, sock):
        self.logger.cubanman.debug(f'deleting and removing {id(sock.sock)} and its reference sock {id(sock.ref_sock.sock)}')
        sock.close()
        sock.ref_sock.close()

        self.instances.remove(sock)
        self.instances.remove(sock.ref_sock)

        del sock.ref_sock
        del sock

                        

    
    def close(self, *args):
        print('\nkeyboard interrupt received, ending ...')
        self.logger.cubanman.debug('SIGINT signal was detected. ending')
        
        for instance in self.instances:
            instance.close()

        self.logger.stopListener()

        sys.exit(0)
