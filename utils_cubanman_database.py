#!/usr/bin/python3
def getRequest(publicIP:str) -> dict:

    if not isinstance(publicIP, str): raise TypeError('variable: "publicIP" must be a string')

    import socket
    #import json

    url = 'ip-api.com'
    request = f'GET http://ip-api.com/json/{publicIP} HTTP/1.1\r\nHost: ip-api.com\r\nAccept: text/json, text/html, text/plain\r\nConnection: close\r\n\r\n'

    s = socket.socket()
    try:
        s.connect((url, 80))
    except OSError:
        return {}

    if s.send(request.encode('utf-8')) != len(request): return {}

    s.settimeout(5)

    try:
        data = s.recv(1024)
    except TimeoutError:
        return {}

    return data.split(b'\r\n\r\n', 1)[1]

def main():
    print(getRequest(b'76.101.126.125'))

if __name__ == '__main__': main()
