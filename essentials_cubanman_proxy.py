#!/usr/bin/python3
import socket
import ssl
import select
import sys
import utils_cubanman_proxy as tools

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

    def fileno(self) -> int:
        return self.sock.fileno()

    def set_status(self, connection):
        self.logger.cubanman.debug(f'setting connection status of {self.name} {id(self.sock)} and {self.ref_sock.name} {id(self.ref_sock.sock)}')
        self.connection = connection
        self.ref_sock.connection = connection

    def recv(self, buffsize):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} receiving data')
        res, connection = tools.recv(self.sock, buffsize, self.logger, self.debug)
        self.set_status(connection)
        return res

    def send(self, res):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending data back')
        if self.sock.send(res) == len(res):
            self.logger.cubanman.debug('success')
            return None

        self.logger.cubanman.debug('failure')

    def go(self, req):
        self.ref_sock.go(req)

    def proxyIt(self, req):
        self.ref_sock.send(req)

    def connected(self) -> bool:
        return self.ref_sock.connected()

    def close(self):
        self.logger.cubanman.debug(f'closing {self.name} {id(self.sock)}')
        self.sock.close()

class Proxy_sock:

    def __init__(self, logger, sock, encryption:int, ca_bundle:str, buffsize:int=1024, ref_sock=None, debug:bool=True):

        self.sock = sock
        self.encryption = encryption
        self.bundle = ca_bundle
        self.buffsize = buffsize
        self.ref_sock = ref_sock
        self.connection = None
        self.web = None
        self.logger = logger
        self.debug = debug

        self.name = self.__class__.__name__

    def fileno(self) -> int:
        return self.sock.fileno()

    def encrypt(self):
        pass

    def settimeout(self,s:int):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} setting a {s} second timeout')
        self.sock.settimeout(s)

    def blocking(self, value:bool):
        self.sock.setblocking(value)

    def close(self):
        self.sock.close()
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} was closed...')

    def set_status(self, connection):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} setting connection status to {connection}')
        self.connection = connection
        self.ref_sock.connection = connection

    def disassemble(self, req) -> tuple:
        return tools.manage_req(req, self.debug)

    def send(self, req):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending data')
        if self.sock.send(req) == len(req):
            self.logger.cubanman.debug('success')
            return None
        self.logger.cubanman.debug('failure')

    def disconnect(self):
        if self.connection == 0: return True
        return False

    def connected(self):
        if self.web == None: 
            return False
        return True

    def go(self, req):
        webserver, port = self.disassemble(req)
        if self.connect(webserver, port):
            self.web = webserver
            self.send(req)
            return True
        return False

    def connect(self, webserver, port) -> bool:

        try:
            self.logger.cubanman.debug(f'{self.name} {id(self.sock)} connecting to {webserver} on {port}')
            self.sock.connect((webserver, port))
            self.settimeout(5)
            return True

        except OSError as e:
            self.logger.cubanman.warning(f'FAILURE cubanman: {self.name} {id(self.sock)} unable to stablish a connection with {self.web}: {e}')
            return False

        except Exception as e:
            self.logger.cubanman.warning(f'cubanman: {e}')
            return False

    def send_back(self, res):
        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} sending back response received from server')
        self.ref_sock.send(res)

    def recv(self) -> bytes:

        self.logger.cubanman.debug(f'{self.name} {id(self.sock)} receiving data from {self.web}')

        response, connection = tools.recv(self.sock, self.buffsize, self.logger, self.debug) 
        
        self.set_status(connection)

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

        self.settimeout(conn_sock, 5) 

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
                        instance.send_back(res)

                        if instance.disconnect() or not res: 
                            self.delPair(instance)

                    else:

                        req = self.instances[0].recv(instance)
                        if req == False:
                            self.delPair(instance)
                        else:

                            #INSTEAD, JUST CHECK IF THE PROXY_SOCK.SOCK IS CONNECTED TO A WEBSERVER OR NOT
                            if not instance.connected():
                                instance.go(req)
                            else:
                                instance.proxyIt(req)

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
