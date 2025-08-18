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

def man_http_msg(response:bytes, logger, status:int=0, debug:bool=False) -> tuple: 
    length = 0

    splitResponse = response.split(b'\r\n\r\n', 1)
    headerStart = splitResponse[0].find(b'Content-Length')

    if headerStart != -1:

            #'Content-Length: ' is 16 characters
        headerStart += 16
        headerEnd = splitResponse[0][(headerStart):].find(b'\r\n')
        contentLength = int(splitResponse[0][headerStart:][:headerEnd])

        #logger.cubanman.info(f'{contentLength}, {len(splitResponse[1])}')
        status = 1
        #logger.cubanman.info(f'[PROXY] |HTTP MSG TYPE| {status}')

        return (contentLength, status, len(splitResponse[1]))

    elif splitResponse[0].find(b'chunked') != -1:
        length = b'-1'
        status = 2


        #logger.cubanman.info(f'[PROXY] |HTTP MSG TYPE| {status}')
        return (length, status, len(splitResponse[1]))

    else:
        length = b'-1'
        status = 3

        print(response)

        #logger.cubanman.info(f'[PROXY] |HTTP MSG TYPE| {status}')
        return (length, status, len(splitResponse[1]))


def connection_status(response, debug) -> int:
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
    status = 0
    totalLength = 0
    dataLength = 0
    connection = 1
    starting = True

    while True:

        try:
            data = conn.recv(buffsize)
        except TimeoutError:
            logger.cubanman.warning(f'timeout. no data was received from: sock{id(conn)}\nhttp-msg: {response}')
            logger.cubanman.debug(f'about http msg: datalength: {dataLength} | totalLength: {totalLength} | msgType: {status} | connectionType: {connection}')
            return (response, connection)

        if not data: 
            logger.cubanman.debug('EOF detected... Closing connection')
            return(data, 0)

        response += data

        if status == 0:
            totalLength, status, dataLength = man_http_msg(data, logger, status, debug)
        if status == 1:
            if not starting: dataLength += len(data)
            if dataLength == totalLength: break
        elif status == 2:
            if data.find(b'\r\n0\r\n\r\n') != -1: break
        else: 
            #status == 3:
            break

        if starting: starting = False
        logger.cubanman.debug(f'loop of recv completed. dataLength: {dataLength} | totalLength: {totalLength}')

    #LATER ON IT MIGHT BE BETTER TO EVALUATE THE CONNECTION HEADER WHEN THE RESPONSE TYPE IS BEING DETERMINED

    connection = connection_status(response, debug)
    logger.cubanman.debug(f'about http msg: datalength: {dataLength} | totalLength: {totalLength} | msgType: {status} | connectionType: {connection}')

    print(response)
    return (response, connection)
