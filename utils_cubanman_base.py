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
        if args.buffsize < 4098:
            args.buffsize = 4098

def ifStls(args:dict) -> None:
    if args.stls:
        args.verify_ca = True
        args.verify_hostname = True
        args.tls = True

def clearLogs() -> None:
    #WORK ON THIS LATER ON
    pass

def saveCurrentConfig(config ,filepath:str='./cubanman_conf.json'):

    config = strDictFormatter(namespaceIntoStr(config))

    try:
        f = open(filepath, 'w')
    except FileNotFoundError:
        raise FileNotFoundError('cubanman: such file was not found')

    f.write(config)

def strDictFormatter(conf:str) -> str:
    for i in range(len(conf)-1, -1, -1):
        if conf[i] == '}': conf = conf[:i]+'\n'+conf[i:]
        elif conf[i] == '{': conf = conf[i]+'\n'+conf[i+1:]
        elif conf[i] == ',': conf = conf[:i+1]+'\n'+conf[i+1:]
    return conf

def namespaceIntoStr(args:object) -> str:
    conf = args.__dict__
    from json import dumps
    return dumps(conf)

def getConfigArgs(filepath:str) -> dict:
    try:
        f = open(filepath, 'r')
    except FileNotFoundError:
        raise FileNotFoundError('cubanman: such file was not found')
    from json import load
    jsonDict = load(f)
    del f

    class Args():
        def __init__(self):
            pass

    args = Args()

    for key, value in jsonDict.items():
        setattr(args, key, value)

    return args



if __name__ == '__main__':
    conf = getConfigArgs('./cubanman_conf.json')
    print(conf, type(conf))
    conf = namespaceIntoStr(conf)
    print(conf, type(conf))
    conf = strDictFormatter(conf)
    print(conf, type(conf))
