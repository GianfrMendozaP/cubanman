import socket

def manage_request(request:bytes, debug:bool) -> tuple:

    if debug: print(f'[SERVER] request: {request}')

    request_lines = request.split(b'\n')

    url = request_lines[0].split()[1]
    if debug: print(f'[SERVER] url: {url}')

    url = fTemp(url)
    if debug: print(f'[SERVER] temp: {url}')

    portP = fPort(url)
    rsrP = fRsr(url)

    if portP == -1 or portP > rsrP:
        port = 80
        webserver = url[:rsrP]

    else:
        port = int((url[portP+1:])[:(rsrP-portP)-1])
        webserver = url[:portP]

    if debug:
        print(f'[SERVER] webserver: {webserver}')
        print(f'[SERVER] port: {port}')

    return (webserver, port, request)

def fPort(url:bytes) -> bytes:
    portP = url.find(b':')
    return portP

def fTemp(url:bytes) -> bytes:
    httpP = url.find(b'://')
    if httpP == -1: return url
    else: return url[(httpP+3):]

def fRsr(url:bytes) -> bytes:
    resourceP = url.find(b'/')
    if resourceP == -1: return len(url)
    else: return resourceP

class Sock():

    def __init__(self, webserver:bytes, port:int, request:bytes, encryption:int, ca_bundle:str, buffsize:int=1024, debug:bool=False):

        self.web = webserver
        self.port = port
        self.req = request
        self.bundle = ca_bundle
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.buffsize = buffsize
        self.debug = debug

    def encrypt(self):
        pass

    def connect(self):

        try:
            self.sock.connect((self.web, self.port))
            if self.debug: print(f'[SERVER] Connection stablished with {self.web}')
            self.settimeout(5)
            #self.blocking(False)
            return True

        except OSError as e:
            print(f'[SERVER] unable to stablish a connection with {str(self.web)}: {e}')
            return False

    def send(self):
        if self.debug: print(f'[SERVER] --> {self.req} --> {self.web}')
        self.sock.send(self.req)

    def recv(self) -> bytes:

        # HANDLE Content-Length SCENARIO
        # HANDLE no Content-Length SCENARIO

        response = b''

        if self.debug: print(f'[SERVER] Now receiving data from {self.web}')
        while True:
            try:
                data = self.sock.recv(self.buffsize)
            except TimeoutError:
                print(f'[SERVER] No data was received from {self.web}')
                break

            if len(data) != 0:
                response += data
            else: break

        setattr(self, 'response', response)

    def cycle(self) -> bytes:
        if self.connect():
            self.send()
            self.recv()
            return self.close()

    def settimeout(self,s:int):
        self.sock.settimeout(s)

    def blocking(self, value:bool):
        self.sock.setblocking(value)

    def close(self):
        self.sock.close()
        if self.debug: print('[SERVER] proxy socket was closed...')
        return self.response



