class Context(_Ctype):
    """Create a new Context instance.
    """
    def __new__(cls, *args):
        if args:
            i = args[0]
            if i == 0:
                return None
            if isinstance(i, _Ints):
                return _Cobject(cls, ctypes.c_void_p(i))
        p = ctypes.c_void_p()
        dll.xnInit(ctypes.byref(p))
        return _Cobject(cls, p)
