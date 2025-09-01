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

def manage_req(request:bytes, debug:bool) -> tuple:

    request_lines = request.split(b'\r\n')

    url = request_lines[0].split()[1]
    if debug: print(f'[REQ_MAN] |URL|: {url}')

    url = fTemp(url)
    if debug: print(f'[REQ_MAN] |TEMP|: {url}')

    portP = fPort(url)
    rsrP = fRsr(url)
    if debug: print(f'[REQ_MAN] |PORT_P|: {portP}')
    if debug: print(f'[REQ_MAN] |RSR_P|: {rsrP}')
    if portP == -1 or portP > rsrP:
        port = 80
        webserver = url[:rsrP]

    else:
        port = int((url[portP+1:])[:(rsrP-portP)-1])
        webserver = url[:portP]

    if debug:
        print(f'[REQ_MAN] |WEBSERVER|: {webserver}')
        print(f'[REQ_MAN] |PORT|: {port}')

    return (webserver, port)

def manHttpMsgType(response:bytes) -> int:

    headerStart = response.find(b'Content-Length')
    contentLength = -1

    if headerStart != -1:
        msgType = 1
        contentLength = getContentLength(headerStart, response)
    elif response.find(b'chunked') != -1:
        msgType = 2
    else:
        msgType = 3

    return (msgType, contentLength)

def getContentLength(headerStart:int, response:bytes):
        headerStart += 16
        headerEnd = response[(headerStart):].find(b'\r\n')
        contentLength = int(response[headerStart:][:headerEnd])

        return contentLength

def connectionStatus(response, debug=False) -> int:
    #if not in response 1 is default
    # 0 = close
    # 1 = keep-alive
    # 2 = upgrade
    # 3 = Proxy-connection

    if response == b'': return 0

    header_start = response.find(b'Connection: ')

    if header_start == -1: 
        if debug: print(f'[CONNECTION_STATUS] |CONNECTION| not found ...')
        return 1

    header_end = response[(header_start+12):].find(b'\r\n')
    header_value = response[(header_start+12):][:header_end]

    if debug: print(f'[CONNECTION_STATUS] |CONNECTION| {header_value}')
    connection = 0

    match header_value:
        case b'close':
            connection = 0
        case b'keep-alive':
            connection = 1
        case b'upgrade':
            connection = 2

    if debug: print(f'CONNECTION STATUS {connection}')
    return connection

def recv(conn, buffsize, logger, debug:bool=False):

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

        if not data: 
            logger.cubanman.debug('EOF detected... Closing connection')
            return(data, 0)

        response += data

        if headers:

            splitResponse = response.split(b'\r\n\r\n', 1)

            if len(splitResponse) == 1: continue
            
            dataLength = len(splitResponse[1])
            msgType, totalLength = manHttpMsgType(splitResponse[0])
            connection = connectionStatus(splitResponse[0])

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
