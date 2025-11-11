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

    def __init__(self, logger, sock, buffsize:int=4098):

        self.sock = sock 
        self.ref_sock = None
        self.connection = None
        self.logger = logger
        self.buffsize = buffsize
        self.name = self.__class__.__name__
        self.https = False

    def fileno(self) -> int:
        return self.sock.fileno()

    def blocking(self, value:bool):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} set blocking mode to {value}')
        self.sock.setblocking(value)

    def settimeout(self,s:int):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} setting a {s} second timeout')
        self.sock.settimeout(s)

    def set_status(self, connection):
        self.logger.cubanman.debug(f'setting connection status of {self.name} {id(self.sock)} and {self.ref_sock.name} {id(self.ref_sock.sock)}')
        self.connection = connection
        self.ref_sock.connection = connection

    def recv(self):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} receiving data')

        if not self.https:
            data, connection = tools.recv(self.sock, self.buffsize, self.ref_sock, self.logger)
            if self.connection == None: self.set_status(connection)
            return data

        return tools.httpsRecv(self.sock, self.buffsize, self.ref_sock, self.logger) 

    def send(self, data):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending data')

        attemps = 2
        while True:
            try:
                bytesSent = self.sock.send(data)
                #print(bytesSent)
                break
            except BrokenPipeError:
                if attemps == 0: return False #disconnect pair
                self.logger.cubanman.warning('cubanman: BrokenPipeError was caught. Retrying...')
            except ConnectionResetError:
                self.logger.cubanman.warning('cubanman: Browser closed connection.')
                return False
            attemps -= 1

        if bytesSent == len(data):
            self.logger.cubanman.debug('success')
            return True
        if bytesSent != 0:
            return self.send(data[bytesSent:])
        return False

    def go(self, data):
        self.settimeout(10)
        return self.ref_sock.go(data)

    def connected(self) -> bool:
        return self.ref_sock.connected()

    def proxyIt(self, data) -> bool:
        return self.ref_sock.send(data)

    def close(self):
        self.sock.close()
        self.connection = None
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} was closed...')

class Proxy_sock(Bws_sock):

    def __init__(self, logger, buffsize:int=4098):

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.buffsize = buffsize
        self.ref_sock = None
        self.connection = None
        self.web = None
        self.httpVersion = None
        self.https = False
        self.x16 = False
        self.logger = logger

        self.name = self.__class__.__name__

    def setHttpVersion(self, version):
        self.httpVersion = version
        self.logger.cubanman.info(f'protocol version was set to {version}')

    def encrypt(self, webserver):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} encrypting connection')
        self.https = True
        self.ref_sock.https = True

    def disassemble(self, data) -> tuple:
        return http.manage_req(data, False)

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

        if http.httpsType(firstLine): self.encrypt(webserver)
        if self.connect(webserver, port):
            self.web = webserver
            if not self.https: return self.send(req)
            return self.send_back(http.connectionResponse(self.httpVersion), self.name)
        return False

    def connect(self, webserver, port) -> bool:
        #Firewall to avoid banned webservers or ports
        if port not in PORTS or webserver in WEBSERVERS: 
            self.logger.cubanman.warning('port or webserver not safe!!!')
            return False

        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} connecting to {webserver} on {port}')
        try:
            self.sock.connect((webserver, port))
        except OSError as e:
            self.logger.cubanman.warning(f'cubanman: {self.name} {id(self.sock)} unable to stablish a connection with {webserver}: {e}')
            return False
        except Exception as e:
            self.logger.cubanman.warning(f'cubanman: unexpected ERROR {e}')
            return False

        self.logger.cubanman.debug('success')
        self.settimeout(10)
        return True

    def send(self, data) -> bool:
        if not self.x16: self.pastFirstx16()
        return super().send(data)

    def send_back(self, data, source:str='webserver'):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending back response received from {source}')
        return self.ref_sock.send(data)

    def recv(self) -> bytes:
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} receiving data from {self.web}')
        if self.connection == None: return b'code-0' 

        if not self.https:
            data, connection = tools.recv(self.sock, self.buffsize, self.ref_sock, self.logger)
            self.set_status(connection)
            return data
        if not self.x16:
            self.logger.cubanman.debug('cubanman: code-0')
            return b'code-0'
        return tools.httpsRecv(self.sock, self.buffsize, self.ref_sock, self.logger)

class Proxy_server:

    def __init__(self, logger, addr:str, port:int, buffsize:int):

        self.addr = addr
        self.port = port
        self.buffsize = buffsize
        self.logger = logger
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

    def fileno(self) -> int:
        return self.sock.fileno()

    def close(self):
        self.logger.cubanman.debug('proxy_server is closing')
        self.sock.close()

    def listen(self):
        self.logger.cubanman.info(f'binding proxy_server to {self.addr} {self.port}')
        try:
            self.sock.bind((self.addr, self.port))
            self.sock.listen()
        except OSError:
            self.logger.cubanman.error('cubanman: conflict when binding address to socket. Maybe address is already being used')
            return False
        except Exception as e:
            self.logger.cubanman.error(f'cubanman: {e}')
            return False

        self.logger.cubanman.info('proxy_server is listening for connections')
        return True

    def accept(self) -> socket.socket:
        conn_sock, _ = self.sock.accept()
        self.logger.cubanman.debug('proxy_server accepted a connection')

        proxy_sock = Proxy_sock(self.logger, self.buffsize)
        bws_sock = Bws_sock(self.logger, conn_sock, self.buffsize)

        proxy_sock.ref_sock = bws_sock
        bws_sock.ref_sock = proxy_sock

        self.logger.cubanman.debug(f'Bws_sock: {id(bws_sock.sock)} <---> Proxy_sock {id(proxy_sock.sock)}')

        return (bws_sock, proxy_sock)

class Processes:

    def __init__(self, logger, server:socket.socket) -> None:

        self.fd = server.fileno()
        self.logger = logger
        self.epoll = select.epoll() 
        self.clients = {}
        self.clients[self.fd] = server

    def start(self) -> None:
        if not self.clients[self.fd].listen(): self.close()
        self.epoll.register(self.fd, select.EPOLLIN)
        self.logger.cubanman.debug('calling epoll.poll')

        while True:

            events = self.epoll.poll()

            for fd, event in events:

                if fd == self.fd:
                    bws_sock, proxy_sock = self.clients[fd].accept() 
                    self.clients[bws_sock.fileno()] = bws_sock
                    self.clients[proxy_sock.fileno()] = proxy_sock
                    self.epoll.register(bws_sock.fileno(), select.EPOLLIN)
                    self.epoll.register(proxy_sock.fileno(), select.EPOLLIN)
                    continue

                if event & select.EPOLLIN:
                    try:
                        data = self.clients[fd].recv()
                    except KeyError as e:
                        self.logger.cubanman.warning(f'cubanman: KeyError:{e}. caused by a socket already deleted. Ignore...')
                        continue
                    match data:
                        case b'code-20':
                            #Indicates some type of OSError like ConnectionReset, BrokenPipe, bad FileDescriptor , etc...
                            self.delPair(self.clients[fd])
                            continue
                        case b'code-10':
                            #This indicates Timeouts that where caught because the server never sent data: data == b''
                            continue
                        case b'code-0':
                            #This indicates necessary omittions in case of expecting an x16 mesage or an SSLWantReadError.
                            continue
                        case b'code-50':
                            #This indicates that cubanman will be shutdown due to an error that needs to be checked.
                            self.close()
                            return None

                        case True:
                            continue
                        case False:
                            self.delPair(self.clients[fd])
                            continue

                    #if not self.doSockets(self.clients[fd], data): self.delPair(self.clients[fd])
                    #continue

                #if event & select.EPOLLHUP:
                #    print('EPOLLHUP FLAG')
                #    self.delPair(self.clients[fd])

    def doSockets(self, client, data) -> bool:
        if not data: return False

        #if returns False, it signals to delete and remove sockets
        if isinstance(client, Proxy_sock):
            return client.send_back(data)

        #then here it's browser_sock
        if client.connected():
            return client.proxyIt(data)

        return client.go(data)


    def delPair(self, sock):
        self.logger.cubanman.debug(f'deleting and removing {id(sock.sock)} and its reference sock {id(sock.ref_sock.sock)}')

        del self.clients[sock.fileno()]
        del self.clients[sock.ref_sock.fileno()]

        self.epoll.unregister(sock.fileno())
        self.epoll.unregister(sock.ref_sock.fileno())
        sock.close()
        sock.ref_sock.close()

        del sock.ref_sock
        del sock




    def close(self, *args):
        print('\nkeyboard interrupt received, ending ...')
        self.logger.cubanman.debug('SIGINT signal was detected. ending')

        if not self.epoll.closed:
            for _, client in self.clients.items():
                self.epoll.unregister(client.fileno())
                client.close()

            self.epoll.close()
        self.logger.stopListener()

        sys.exit(0)
