#!/usr/bin/python3

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

    url = fTemp(url)

    portP = fPort(url)
    rsrP = fRsr(url)
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

def transferType(response:bytes) -> int:

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

    if response == b'': return 0

    header_start = response.find(b'\r\nConnection: ')

    if header_start == -1:
        if debug: print(f'[CONNECTION_STATUS] |CONNECTION| not found ...')
        return 1

    header_end = response[(header_start+14):].find(b'\r\n')
    header_value = response[(header_start+14):][:header_end]

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

def getFirstLine(msg:bytes) -> bytes:
    firstLine = msg.split(b'\r\n', 1)
    return firstLine[0]

def httpVersion(firstLine:bytes) -> bytes:
    #HERE ADD LOGIC TO DETECT HTTP VERSION
    values = firstLine.split()

    return values[2]

def osType(firstLine:bytes) -> bytes:
    #HERE ADD LOGIC TO DETECT OS
    pass

def getBrowser(firstLine:bytes) -> bytes:
    #HERE ADD LOGIC TO DETECT BROWSER
    pass

def httpsType(firstLine:bytes) -> bool:
    #True == https
    #False == http
    if firstLine.find(b'CONNECT') != -1:
        return True
    return False

def connectionResponse(version) -> bytes:
    res = f'{version} 200 Connection Established\r\nContent-Length: 0\r\n\r\n'.encode('utf-8')
    print(res)
    return res
