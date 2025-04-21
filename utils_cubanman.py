def padding(msg:str, Format) -> tuple:

    stdin = msg.encode(Format)
    stdinlen = str(len(stdin)).encode(Format)
    stdinlen = stdinlen + (b' ' * (self.buffsize - len(stdinlen)))
    return(stdin, stdinlen)

