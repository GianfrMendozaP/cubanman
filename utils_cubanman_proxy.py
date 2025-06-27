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

    if debug: print(f'[REQ_MAN] |REQUEST|: {request}')

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

def man_http_msg(response:bytes, length:bytes, status:int=0, debug:bool=False) -> tuple:

    #keepAlive = None
    splitResponse = response.split(b'\r\n\r\n')
    headerStart = splitResponse[0].find(b'Content-Length')
    #if response.find(b'Connection: keep-alive') != -1: keepAlive = True
    #if response.find(b'Connection: close') != 1: keepAlive = False

    if headerStart != -1:

            #'Content-Length: ' is 16 characters
        headerStart += 16
        headerEnd = splitResponse[0][(headerStart):].find(b'\r\n')
        contentLength = int(splitResponse[0][headerStart:][:headerEnd])

        if debug: print(f'[MAN_RES] |MSG| Content-Length: {contentLength}')

        status = 1

        return (contentLength, status)

    elif splitResponse[0].find(b'chunked') != -1:
        length = b'-1'
        status = 2

        return (length, status)

    else:
        length = b'-1'
        status = 3

        return (length, status)


def connection_status(response) -> int:
    # -1 = Not in response
    # 0 = close
    # 1 = keep-alive
    # 2 = upgrade
    # 3 = Proxy-connection

    if response == b'': return 0

    header_start = response.find(b'Connection: ')
    if header_start == -1: return 1
    header_end = response[header_start:].find(b'\r\n')
    header_value = response[(header_start+12):][:header_end]

    print(header_value)
    connection = None

    match header_value:
        case b'close':
            connection = 0
        case b'keep-alive':
            connection = 1
        case b'upgrade':
            connection = 2
        case b'Proxy-connection':
            connection = 3

    return int(connection)

def recv(conn, buffsize, debug:bool=False):

    response = b''
    status = 0
    length = b''
    connection = 0

    while True:

        try:
            data = conn.recv(buffsize)
        except TimeoutError:
            print('[PROXY] |RECEIVING| No data was received...')
            return response

        if not data: break
        response += data

        if status == 0:
            length, status = man_http_msg(data, length, status, debug)
        if status == 1:
            if len(response) == length: break
        if status == 2:
            if data.find(b'\r\n0\r\n\r\n') != -1: break

    if status != 3: connection = connection_status(response)

    return (response, connection)
