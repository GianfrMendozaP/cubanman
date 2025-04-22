def padding(msg:str, Format, buffsize:int) -> tuple:

    stdin = msg.encode(Format)
    stdinlen = str(len(stdin)).encode(Format)
    stdinlen = stdinlen + (b' ' * (buffsize - len(stdinlen)))
    return(stdin, stdinlen)

