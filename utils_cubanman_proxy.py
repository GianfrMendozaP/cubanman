import socket
import utils_cubanman_http_headers as http
import utils_cubanman_tls_records as tlsRec
from ssl import SSLWantReadError

certBundle = '/etc/ssl/certs/ca-certificates.crt'

def recv(conn, buffsize, ref_sock, logger):

    response = b''
    msgType = 0
    totalLength = 0
    dataLength = 0
    connection = None
    headers = True
    proxyConnected = ref_sock.connected()

    while True:

        try:
            data = conn.recv(buffsize)
        except TimeoutError:
            logger.cubanman.warning(f'timeout. no data was received from: sock{id(conn)}\nhttp-msg: {response}')
            logger.cubanman.debug(f'about http msg: datalength: {dataLength} | totalLength: {totalLength} | msgType: {msgType} | connectionType: {connection}')
            return (response, 0)
        except SSLWantReadError:
            logger.cubanman.debug(f'SSLWantReadError was caught and will be ignored')
            if response == b'': return(b'code-20', -1)

        if not data: 
            logger.cubanman.debug('EOF detected... Closing connection')
            return(False, 0)

        response += data

        if headers:

            splitResponse = response.split(b'\r\n\r\n', 1)

            if len(splitResponse) == 1: continue
            
            dataLength = len(splitResponse[1])
            msgType, totalLength = http.transferType(splitResponse[0])
            connection = http.connectionStatus(splitResponse[0])

        if proxyConnected: 
            if not ref_sock.send(data): return (False, 0)

        print(f'totalReceived: {len(response)} | dataJReceived: {len(data)}')

        match msgType:

            case 1: 
                if not headers: dataLength += len(data)
                if dataLength == totalLength: return (True, connection)
            case 2:
                if not headers: dataLength += len(data)
                if response.find(b'\r\n0\r\n\r\n') != -1: return (True, connection)
            case 3:
                #msgType
                if proxyConnected: return(True, connection)
                return (ref_sock.go(response), connection)

        if headers: headers = False

    #logger.cubanman.debug(f'about http msg: datalength: {dataLength} | totalLength: {totalLength} | msgType: {msgType} | connectionType: {connection}')

    #print(response)

    #if connectHttps: return (ref_sock.go(response), connection)
    #return (True, connection)

def httpsRecv(conn, buffsize, ref_sock, logger, https:bool=False):

    response = b''
    dataLength = 0
    loop = 0

    while True:
        loop += 1

        try:
            data = conn.recv(buffsize)
        except TimeoutError:
            logger.cubanman.warning(f'cubanman: Timeout was caught...')
            if response == b'': return b'code-10'
            print(f'tls/ssl response: {response}')
            return b'code-50'
        except OSError as e:
            logger.cubanman.critical(f'cubanman: {e}')
            print('socket:', id(conn))
            return b'code-20'

        if not data: return False
        
        response += data
        #dataLength += len(data)
    

        if not ref_sock.send(data): return False

        #later on call x16Scan on data, and separate data of the previous x16 from the new x16
        #make sure the first byte starts with x16, if not find it and then split data, make sure
        #no more x16s are sent in tls records, if not it might get tricky
        bytesLeft = tlsRec.x16Scan(response)
        print(f'bytesLeft: {bytesLeft} | datalength {len(response)} | loop {loop}')
        if bytesLeft == 0: return True


    #kind = response[0] if response else 'disconnect'
    #logger.cubanman.debug(f'about https msg: messageType: {kind} | datalength: {dataLength}')

    #print(response)
    #return(response)


def dataFilter(data) -> bool:
    match data:
        case b'code-20':
            #Indicates some type of OSError like ConnectionReset, BrokenPipe, bad FileDescriptor , etc...
            self.delPair(self.clients[fd])
            return False
        case b'code-10':
            #This indicates Timeouts that where caught because the server never sent data: data == b''
            return False
        case b'code-0':
            #This indicates necessary omittions in case of expecting an x16 mesage or an SSLWantReadError.
            return True
        case b'code-50':
            #This indicates that cubanman will be shutdown due to an error that needs to be checked.
            return False
        case True:
            return True
        case False:
            return False
        case _:
            return False



















