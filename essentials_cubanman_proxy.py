#!/usr/bin/python3
import socket
import ssl
import select
import sys
import utils_cubanman_proxy as tools

class Bws_sock:

    def __init__(self, sock, ref_sock=None, debug:bool=False):

        self.sock = sock
        self.ref_sock = ref_sock
        self.connection = None
        self.debug = False

    def fileno(self) -> int:
        return self.sock.fileno()

    def send(self, res):
        return self.sock.send(res)

    def recv(self, buffsize):
        res, self.connection = tools.recv(self.sock, buffsize, self.debug)
        return res

    def send(self, res):
        self.sock.send(res)

    def close(self):
        if self.debug: print('[BWS_CLIENT] |CLOSING|')
        self.sock.close()

class Proxy_sock:

    def __init__(self, sock, encryption:int, ca_bundle:str, buffsize:int=1024, ref_sock=None, debug:bool=False):

        self.sock = sock
        self.encryption = encryption
        self.bundle = ca_bundle
        self.buffsize = buffsize
        self.ref_sock = ref_sock
        self.connection = None
        self.web = None
        self.debug = debug

    def fileno(self) -> int:
        return self.sock.fileno()

    def encrypt(self):
        pass

    def settimeout(self,s:int):
        self.sock.settimeout(s)

    def blocking(self, value:bool):
        self.sock.setblocking(value)

    def close(self):
        self.sock.close()
        if self.debug: print('[PROXY] |CLOSING| Proxy socket was closed...')

    def set_status(self, connection):
        self.connection = connection
        self.ref_sock.connection = connection

    def disassemble(self, req) -> tuple:
        return tools.manage_req(req, self.debug)

    def send(self, req):
        self.sock.send(req)

    def disconnect(self):
        if self.connection == 0: return True
        return False

    def go(self, req):
        webserver, port = self.disassemble(req)
        if self.connect(webserver, port):
            self.send(req)
            self.web = webserver
            return True
        return False

    def connect(self, webserver, port) -> bool:

        try:
            self.sock.connect((webserver, port))
            if self.debug: print(f'[PROXY] |CONNECTION| Connection stablished with {self.web}')
            self.settimeout(10)
            return True

        except OSError as e:
            print(f'[PROXY] |ERROR| unable to stablish a connection with {str(self.web)}: {e}')
            return False

    def send_back(self, res):
        self.ref_sock.send(res)

    def recv(self) -> bytes:

        if self.debug: print(f'[PROXY] |RECEIVING| data from {self.web}')

        response, connection = tools.recv(self.sock, self.buffsize, self.debug)
        if self.debug:
            print(f'[PROXY] |CONNECTION| {connection}')
            print(f'[PROXY] |RESPONSE| {response}')
        
        self.set_status(connection)

        return (response)


class Proxy_server:
    
    def __init__(self, addr:str, port:int, buffsize:int, debug:bool=False):

        self.addr = addr
        self.port = port
        self.buffsize = buffsize
        self.debug = debug
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

        #if self.encryption != 0: self.encrypt()

    @staticmethod
    def settimeout(conn, value):
        conn.settimeout(value)

    def fileno(self) -> int:
        return self.sock.fileno()

    def close(self):
        self.sock.close()

    def listen(self):

        try:
            self.sock.bind((self.addr, self.port))
            if self.debug: print(f'[SERVER] |BINDING| socket was bound to {self.addr} {self.port}')

        except OSError:
            print('[SERVER] |ERROR| Conflict when binding address to socket. Maybe address is already being used')
            sys.exit(1)

        self.sock.listen()
        if self.debug: print('[SERVER] |LISTENING| listening for connections')

    def accept(self) -> socket.socket:
        conn_sock, details = self.sock.accept()
        if self.debug: print(f'[SERVER] |CONNECTION| connection accepted {details}')
        del details

        self.settimeout(conn_sock, 15)

        proxy_sock = Proxy_sock(socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM), 0, None, self.buffsize, None, self.debug)
        bws_sock = Bws_sock(conn_sock, None, self.debug)

        proxy_sock.ref_sock = bws_sock
        bws_sock.ref_sock = proxy_sock

        return (bws_sock, proxy_sock)
    
    def recv(self, conn) -> bool:

        data = conn.recv(self.buffsize)

        if not data:
            if self.debug: print('[SERVER] |DISCONNECTION| a client has disconnected')
            return False

        return data

class Processes:

    def __init__(self, instances:list, debug:bool=False) -> None:

        self.instances = instances
        self.debug = debug

    def start(self) -> None:
        self.instances[0].listen()
        if self.debug: print('[PROCESSES] starting main loop')

        while True:

            ready, _, _ = select.select(self.instances, [], [])

            for instance in ready:

                if instance == self.instances[0]:
                    bws_client, proxy_sock = self.instances[0].accept()

                    self.instances.extend([bws_client, proxy_sock])

                else:

                    if isinstance(instance, Proxy_sock):

                        res = instance.recv()
                        instance.send_back(res)

                        if instance.disconnect(): self.delPair(instance)

                    else:

                        req = self.instances[0].recv(instance)
                        if req == False: delPair(instance)

                        if instance.ref_sock.connection == None:
                            instance.ref_sock.go(req)
                        else:
                            instance.ref_sock.send(req)

    def delPair(self, sock):
        sock.close()
        sock.ref_sock.close()

        self.instances.remove(sock)
        self.instances.remove(sock.ref_sock)

        del sock.ref_sock
        del sock

                        

    
    def close(self, *args):
        print('\nkeyboard interrupt received, ending ...')
        
        for instance in self.instances:
            instance.close()

        sys.exit(0)
