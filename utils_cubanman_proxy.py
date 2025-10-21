import socket
import utils_cubanman_http_headers as http
import utils_cubanman_tls_records as tlsRec
from ssl import SSLWantReadError

certBundle = '/etc/ssl/certs/ca-certificates.crt'

def recv(conn, buffsize, logger):

    response = b''
    msgType = 0
    totalLength = 0
    dataLength = 0
    connection = None
    headers = True

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
            return(data, 0)

        response += data

        if headers:

            splitResponse = response.split(b'\r\n\r\n', 1)

            if len(splitResponse) == 1: continue
            
            dataLength = len(splitResponse[1])
            msgType, totalLength = http.transferType(splitResponse[0])
            connection = http.connectionStatus(splitResponse[0])

        match msgType:

            case 1: 
                if not headers: dataLength += len(data)
                if dataLength == totalLength: break
            case 2:
                if not headers: dataLength += len(data)
                if response.find(b'\r\n0\r\n\r\n') != -1: break
            case 3:
                #msgType 3
                break

        if headers: headers = False

    logger.cubanman.debug(f'about http msg: datalength: {dataLength} | totalLength: {totalLength} | msgType: {msgType} | connectionType: {connection}')

    print(response)
    return (response, connection)

def httpsRecv(conn, buffsize, logger, https:bool=False):

    response = b''
    dataLength = 0
    loopCount = 0

    while True:
        loopCount += 1
        if loopCount == 1000:
            logger.cubanman.debug('loopCount is 1000')
        #if loopCount == 50: 
        #    logger.cubanman.critical('records are not being measured correctly. Ending')
        #    return b'code-50'

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
            return b'code-50'

        if not data: break
          

        response += data
        dataLength += len(data)
        #later on call x16Scan on data, and separate data of the previous x16 from the new x16
        #make sure the first byte starts with x16, if not find it and then split data, make sure
        #no more x16s are sent in tls records, if not it might get tricky
        bytesLeft = tlsRec.x16Scan(response)
        
        print(f'bytesLeft: {bytesLeft} | datalength {len(response)}')
        
        if bytesLeft == 0: break


    kind = response[0] if response else 'disconnect'
    logger.cubanman.info(f'about https msg: messageType: {kind} | datalength: {dataLength}')

    #print(response)
    return(response)
