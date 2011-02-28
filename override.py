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
            elif isinstance(i, basestring):
                # Init from XML file
                p = ctypes.c_void_p()
                err = EnumerationErrors()
                status = dll.xnInitFromXmlFile(i, p, err)
                if status:
                    raise Exception("Error %s: %s" % (dll.xnGetStatusName(status),
                                                      dll.xnGetStatusString(status)))

        p = ctypes.c_void_p()
        status = dll.xnInit(ctypes.byref(p))
        if status:
            raise Exception("Error %s: %s" % (dll.xnGetStatusName(status),
                                              dll.xnGetStatusString(status)))
        return _Cobject(cls, p)

    def StatusName(self, status):
        return dll.xnGetStatusName(status)

    def StatusString(self, status):
        return dll.xnGetStatusString(status)

class NodeQuery(_Ctype):
    """Create a new NodeQuery instance.

    # FIXME: handle destruction
    """
    def __new__(cls, *args):
        if args and args[0]:
            p = args[0]
        else:
            p = ctypes.c_void_p()
            dll.xnNodeQueryAllocate(ctypes.byref(p))
        return _Cobject(cls, p)

class EnumerationErrors(_Ctype):
    """Create a new EnumerationErrors instance.

    # FIXME: handle destruction
    """
    def __new__(cls, *args):
        if args and args[0]:
            p = args[0]
        else:
            p = ctypes.c_void_p()
            dll.xnEnumerationErrorsAllocate(ctypes.byref(p))
        return _Cobject(cls, p)

class NodeInfoList(_Ctype):
    """Create a new NodeInfoList instance.

    # FIXME: handle destruction
    """
    def __new__(cls, *args):
        if args and args[0]:
            p = args[0]
        else:
            p = ctypes.c_void_p()
            dll.xnNodeInfoListAllocate(ctypes.byref(p))
        return _Cobject(cls, p)

