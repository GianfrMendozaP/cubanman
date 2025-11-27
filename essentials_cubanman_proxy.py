#!/usr/bin/python3
import socket
import ssl
import select
import sys
import utils_cubanman_proxy as tools
import utils_cubanman_http_headers as http
import threading
from time import sleep

PORTS = [443, 80, 88]
WEBSERVERS = []

class Bws_sock:

    def __init__(self, logger, sock, buffsize:int, timeout:float):

        self.sock = sock 
        self.ref_sock = None
        self.connection = None
        self.logger = logger
        self.buffsize = buffsize
        self.name = self.__class__.__name__
        self.https = False
        self.timeout = timeout

    def fileno(self) -> int:
        return self.sock.fileno()

    def blocking(self, value:bool):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} set blocking mode to {value}')
        self.sock.setblocking(value)

    def settimeout(self):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} setting a {self.timeout} second timeout')
        self.sock.settimeout(self.timeout)

    def set_status(self, connection):
        self.logger.cubanman.debug(f'setting connection status of {self.name} {id(self.sock)} and {self.ref_sock.name} {id(self.ref_sock.sock)}')
        self.connection = connection
        self.ref_sock.connection = connection

    def recv(self):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} is receiving data')
        data = None

        if not self.https:
            data, connection = tools.recv(self.sock, self.buffsize, self.ref_sock, self.logger)
            if self.connection == None: self.set_status(connection)
        else:
            data =  tools.httpsRecv(self.sock, self.buffsize, self.ref_sock, self.logger) 
        
        return data

    def send(self, data):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending data')

        while True:
            try:
                bytesSent = self.sock.send(data)
                break
            except BrokenPipeError:
                self.logger.cubanman.warning('cubanman: BrokenPipeError was caught')
                return False
            except ConnectionResetError:
                self.logger.cubanman.warning('cubanman: Browser closed connection.')
                return False
            except OSError as e:
                self.logger.cubanman.warning(f'cubanman: {e} on {self.name} {id(self.sock)}\nmessage: {data}')
                return False

            attemps -= 1

        if bytesSent == len(data):
            self.logger.cubanman.debug('success')
            return True
        if bytesSent != 0:
            return self.send(data[bytesSent:])
        return False

    def go(self, data):
        self.settimeout()
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

    def __init__(self, logger, buffsize, timeout:float):

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
        self.timeout = timeout 

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
        self.settimeout()
        return True

    def send(self, data) -> bool:
        if not self.x16: self.pastFirstx16()
        return super().send(data)

    def send_back(self, data, source:str='webserver'):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending back response received from {source}')
        return self.ref_sock.send(data)

    def recv(self) -> bytes:
        if self.connection == None: return b'code-0' 
        if not self.x16:
            self.logger.cubanman.debug('cubanman: code-0')
            return b'code-0'
        
        return super().recv()

class Thread_bws_sock(Bws_sock):
    
    def __init__(self, logger, sock, buffsize:int, timeout):
        super().__init__(logger, sock, buffsize, timeout)


    def recv(self, threads:list, allThreadSockets:dict):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} receiving data')

        threadProxySockCreated = False

        while True:
            data = None 
        
            if not self.https:
                data, connection = tools.recv(self.sock, self.buffsize, self.ref_sock, self.logger)
                if self.connection == None: self.set_status(connection)
            else:
                data =  tools.httpsRecv(self.sock, self.buffsize, self.ref_sock, self.logger) 
                if not self.ref_sock.x16: self.ref_sock.pastFirstx16()

            if threadProxySockCreated == False:
                self.threadProxySock(threads, allThreadSockets)
                threadProxySockCreated = True

            if not tools.dataFilter(data):
                self.ref_sock.send(''.encode('utf-8'))
                self.close()
                return None
    
    def threadProxySock(self, threads, allThreadSockets):
        thread = threading.Thread(target=self.ref_sock.recv, daemon=True)
        thread.start()
        threads.append(thread)
        allThreadSockets[id(thread)] = self.ref_sock

class Thread_proxy_sock(Proxy_sock):

    def __init__(self, logger, buffsize:int, timeout):
        super().__init__(logger, buffsize, timeout)

    def recv(self):
       
        while not self.x16:
            sleep(0.5)

        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} receiving data')

        while True:
            data = None 
        
            if not self.https:
                data, connection = tools.recv(self.sock, self.buffsize, self.ref_sock, self.logger)
                if self.connection == None: self.set_status(connection)
            else:
                data =  tools.httpsRecv(self.sock, self.buffsize, self.ref_sock, self.logger)

            if not tools.dataFilter(data):
                self.send_back(''.encode('utf-8'), self.name)
                self.close()
                return None
    
class Mixed_bws_sock(Bws_sock):

    def __init__(self, logger, sock, buffsize:int, timeout):
        self.alive = True
        super().__init__(logger, sock, buffsize, timeout)

    def recv(self):
        data = None

        if not self.https:
            data, connection = tools.recv(self.sock, self.buffsize, self.ref_sock, self.logger)
            if self.connection == None: self.set_status(connection)
        else:
            data =  tools.httpsRecv(self.sock, self.buffsize, self.ref_sock, self.logger) 
        
        self.alive = tools.dataFilter(data)
 

class Mixed_proxy_sock(Proxy_sock):

    def __init__(self, logger, buffsize:int, timeout):
        self.alive = True
        super().__init__(logger, buffsize, timeout)

    def recv(self):
       
        if not self.x16: return None

        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} receiving data')
 
        data = None 
        
        if not self.https:
            data, connection = tools.recv(self.sock, self.buffsize, self.ref_sock, self.logger)
            if self.connection == None: self.set_status(connection)
        else:
            data =  tools.httpsRecv(self.sock, self.buffsize, self.ref_sock, self.logger)

        self.alive = tools.dataFilter(data)


class Proxy_server:

    def __init__(self, logger, addr:str, port:int, buffsize:int, useThreads:bool, threadedEpoll:bool, timeout:float):

        self.addr = addr
        self.port = port
        self.buffsize = buffsize
        self.logger = logger
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.useThreads = useThreads
        self.mixed = threadedEpoll 
        self.timeout = timeout

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

    def accept(self) -> tuple:
        conn_sock, _ = self.sock.accept()
        self.logger.cubanman.debug('proxy_server accepted a connection')

        if self.useThreads:
            proxy_sock = Thread_proxy_sock(self.logger, self.buffsize, self.timeout)
            bws_sock = Thread_bws_sock(self.logger, conn_sock, self.buffsize, self.timeout)
        
        elif self.mixed:
            
            proxy_sock = Mixed_proxy_sock(self.logger, self.buffsize, self.timeout)
            bws_sock = Mixed_bws_sock(self.logger, conn_sock, self.buffsize, self.timeout)

        else:
            proxy_sock = Proxy_sock(self.logger, self.buffsize, self.timeout)
            bws_sock = Bws_sock(self.logger, conn_sock, self.buffsize, self.timeout)

        proxy_sock.ref_sock = bws_sock
        bws_sock.ref_sock = proxy_sock

        self.logger.cubanman.debug(f'Bws_sock: {id(bws_sock.sock)} <---> Proxy_sock {id(proxy_sock.sock)}')

        return (bws_sock, proxy_sock)

class Processes:

    def __init__(self, logger, server:socket.socket, timeout:float) -> None:

        self.fd = server.fileno()
        self.logger = logger
        self.epoll = None 
        self.clients = {}
        self.clients[self.fd] = server
        self.threads = []
        self.alive = True
        self.allThreadSockets = {}
        self.cleaner:threading.Thread = None
        self.timeout = timeout


    def epollStart(self) -> None:
        self.logger.cubanman.info('using epoll')
        if not self.clients[self.fd].listen(): self.close()
        self.epoll = select.epoll() 
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

                    if not tools.dataFilter(data):
                        self.delPair(self.clients[fd])

    def threadedStart(self):
        self.logger.cubanman.info('using threads')
        if not self.clients[self.fd].listen(): self.close()
        self.cleaner = threading.Thread(target=self.threadCleaner, daemon=True)
        self.cleaner.start()
        print(f'active threads: {threading.active_count()}')

        while True:
            bws_sock, proxy_sock = self.clients[self.fd].accept() 
            addr = id(self.threadIt(bws_sock))
            self.allThreadSockets[addr] = bws_sock
            print(f'threads: {len(self.threads)}')

    def threadedEpoll(self):
        self.logger.cubanman.info('using threadedEpoll')
        if not self.clients[self.fd].listen(): self.close()
        print(f'active threads: {threading.active_count()}')
        
        self.epoll = select.epoll() 
        self.epoll.register(self.fd, select.EPOLLIN)
        self.logger.cubanman.debug('calling epoll.poll')

        while True:
            
            events = self.epoll.poll()

            for fd, event in events: 

                if fd == self.fd:
                    
                    print(f'active threads: {threading.active_count()} --------------- threads {len(self.threads)}')
                    bws_sock, proxy_sock = self.clients[fd].accept() 
                    self.clients[bws_sock.fileno()] = bws_sock
                    self.clients[proxy_sock.fileno()] = proxy_sock
                    self.epoll.register(bws_sock.fileno(), select.EPOLLIN)
                    self.epoll.register(proxy_sock.fileno(), select.EPOLLIN)
                    continue

                if event & select.EPOLLIN:
                    thread = threading.Thread(target=self.clients[fd].recv, args=[])
                    self.logger.cubanman.debug(f'thread {id(thread)} is starting -> {self.clients[fd].name} {id(self.clients[fd].sock)}')
                    thread.start()
                    self.threads.append(thread)
                    self.allThreadSockets[id(thread)] = fd

            self.altThreadCleaner()
#THIS CAN BE DONE IN THREADCLEANER BUT NEEDS A BIT OF TINKERING

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

    def threadIt(self, bws_sock:Thread_bws_sock):
        self.logger.cubanman.debug(f'threading {bws_sock.name} {id(bws_sock.sock)}')
        thd =  threading.Thread(target=bws_sock.recv, args=[self.threads, self.allThreadSockets], daemon=True)
        thd.start()
        self.threads.append(thd)
        return thd

    def threadCleaner(self):
        self.logger.cubanman.debug('thread cleaner is starting')
        while True:
            for i in range((len(self.threads)-1), -1, -1):
                self.threads[i].join(timeout=0.0)
                if not self.threads[i].is_alive(): 
                    addr = id(self.threads[i])
                    self.logger.cubanman.debug(f'cleaner just joint {id(self.allThreadSockets[addr].sock)} {self.allThreadSockets[addr].name}')
                    del self.allThreadSockets[addr] 
                    del self.threads[i]

            if not self.alive and len(self.threads) == 0: 
                self.logger.cubanman.debug('cleaner thread has ended its task')
                return None
            sleep(1.0)

    def altThreadCleaner(self):
        self.logger.cubanman.debug('cleaning lazy threads')
        for i in range(len(self.threads)-1, -1, -1):
            self.threads[i].join()
            self.logger.cubanman.debug(f'thread {id(self.threads[i])} was joint')
            fd = self.allThreadSockets[id(self.threads[i])]
            del self.threads[i]

            try: 
                if not self.clients[fd].alive:
                    self.delPair(self.clients[fd])
            except KeyError as e:
                self.logger.cubanman.warning(f'cubanman: KeyError:{e}. caused by a socket already deleted. Ignore...')

        if len(self.threads) != 0:
            self.logger.cubanman.error('some lazy threads somehow doged the cleaner')
            self.close()

    def broadcastEOF(self):
        if len(self.allThreadSockets) == 0: return None
        self.logger.cubanman.debug('broadcasting EOF to allThreadSockets')
        for _, sock in self.allThreadSockets.items():
            for _ in range(5):
                if not sock.send(''.encode()): break
        
        self.logger.cubanman.debug('EOF was broadcast')

    def endEpoll(self):
        if self.epoll == None: return None
        self.logger.cubanman.debug('ending epolling')
        if not self.epoll.closed:
            for _, client in self.clients.items():
                self.epoll.unregister(client.fileno())
                client.close()
            self.epoll.close()

    def close(self, *args):
        print('\nkeyboard interrupt received, ending ...')
        self.logger.cubanman.debug('SIGINT signal was detected. ending')
        self.alive = False

        self.endEpoll()

        if self.cleaner != None:
            self.broadcastEOF()
            self.cleaner.join()
        else:
            self.altThreadCleaner()

        self.logger.stopListener()
        print('bye...')

        sys.exit(0)
