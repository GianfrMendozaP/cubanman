def padding(msg:str, Format, buffsize:int) -> tuple:

    stdin = msg.encode(Format)
    stdinlen = str(len(stdin)).encode(Format)
    stdinlen = stdinlen + (b' ' * (buffsize - len(stdinlen)))
    return(stdin, stdinlen)

def whichEnc(args:dict) -> int:

    if args.tls: return 1
    if args.tls1v1: return 2
    if args.tls1v2: return 3
    return 0

def ifProxy(args:dict) -> None:
    if args.proxy:
        args.static = True
        if args.buffsize < 1024:
            args.buffsize = 1024

def ifStls(args:dict) -> None:
    if args.stls:
        args.verify_ca = True
        args.verify_hostname = True
        args.tls = True

def clearLogs() -> None:
    #WORK ON THIS LATER ON
    pass
