import socket

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

def manage_request(request:bytes, debug:bool) -> tuple:

    if debug: print(f'[PROXY] |REQUEST|: {request}')

    request_lines = request.split(b'\n')

    url = request_lines[0].split()[1]
    if debug: print(f'[PROXY] |URL|: {url}')

    url = fTemp(url)
    if debug: print(f'[PROXY] |TEMP|: {url}')

    portP = fPort(url)
    rsrP = fRsr(url)

    if portP == -1 or portP > rsrP:
        port = 80
        webserver = url[:rsrP]

    else:
        port = int((url[portP+1:])[:(rsrP-portP)-1])
        webserver = url[:portP]

    if debug:
        print(f'[PROXY] |WEBSERVER|: {webserver}')
        print(f'[PROXY] |PORT|: {port}')

    return (webserver, port, request)

class Sock():

    def __init__(self, webserver:bytes, port:int, request:bytes, encryption:int, ca_bundle:str, buffsize:int=1024, debug:bool=False):

        self.web = webserver
        self.port = port
        self.req = request
        self.bundle = ca_bundle
        self.sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.buffsize = buffsize
        self.debug = debug
        self.contentLength = 0
        self.dataLen = 0

    def encrypt(self):
        pass

    def connect(self):

        try:
            self.sock.connect((self.web, self.port))
            if self.debug: print(f'[PROXY] |CONNECTION| Connection stablished with {self.web}')
            self.settimeout(5)
            #self.blocking(False)
            return True

        except OSError as e:
            print(f'[PROXY] |ERROR| unable to stablish a connection with {str(self.web)}: {e}')
            return False

    def send(self):
        #if self.debug: print(f'[SERVER] --> {self.req} --> {self.web}')
        self.sock.send(self.req)

    def recv(self) -> bytes:

        # HANDLE Content-Length SCENARIO
        # HANDLE no Content-Length SCENARIO

        response = b''

        if self.debug: print(f'[PROXY] |RECEIVING| data from {self.web}')
        while True:
            try:
                data = self.sock.recv(self.buffsize)
            except TimeoutError:
                print(f'[PROXY] No data was received from {self.web}')
                break

            response += data
            print(f'[PROXY] |INCOMPLETE RESPONSE|: {response}')
            if self.isComplete(response): break

        setattr(self, 'response', response)

    def isComplete(self, response:bytes) -> bool:

        headerStart = response.find(b'Content-Length')

        if headerStart != -1:

            #'Content-Length: ' is 16 characters
            headerStart += 16
            splitResponse = response.split(b'\r\n\r\n')
            headerEnd = splitResponse[0][(headerStart):].find(b'\r\n')
            contentLength = int(splitResponse[0][headerStart:][:headerEnd])
            if self.debug: print(f'[PROXY] |RESPONSE| Content-Length: {contentLength}')
            if not len(splitResponse[1]) == contentLength: 

                self.contentLength = contentLength
                self.dataLen = len(splitResponse[1])
                return False
            if self.debug: print('[PROXY] |RESPONSE| complete!')
            return True


        elif self.dataLen != 0 and self.contentLength != 0:

            self.dataLen += len(response)
            if self.dataLen == self.contentLength: return True
            return False

        else:
            #temporary!!!!!
            #EVALUATE CHUNKS OF DATA!!!!!!
            print('chunked transfer encoding.....')
            return True





    def cycle(self) -> bytes:
        if self.connect():
            self.send()
            self.recv()
            self.close()
            return self.response

    def settimeout(self,s:int):
        self.sock.settimeout(s)

    def blocking(self, value:bool):
        self.sock.setblocking(value)

    def close(self):
        self.sock.close()
        if self.debug: print('[PROXY] |CLOSING| Proxy socket was closed...')



