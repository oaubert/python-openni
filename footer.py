
# Start of footer.py #

def error(s):
    xnPrintError(s, "OpenNI error")

def debug(*args):
    '''Example callback, useful for debugging.
    '''
    print('Debug callback (%s)' % ', '.join(args))

if __name__ == '__main__':
    import time

    #c = Context('/home/oaubert/src/kinect/Nite-1.3.0.18/Data/Sample-User.xml')
    c = Context()
    q=NodeQuery()
    err = EnumerationErrors()

    #q.setCreationInfo("Foo")
    #q.addSupportedCapability("Mirror")
    #output = MapOutputMode(640, 480, 30)
    #q.addSupportedMapOutputMode(output)    
    #c.createDepthGenerator(q, err)
    
    u=c.createUserGenerator(q)
    if not u.isCapabilitySupported('User::Skeleton'):
        raise "Unable to create UserGenerator"
    h=u.registerUserCallbacks(cb.UserHandler(debug), cb.UserHandler(debug), "User")
    print "Registered cb %x" % h
    s=c.startGeneratingAll()
    if s:
        error(s)
    for i in range(4):
        s=c.waitNoneAndUpdateAll()
        if s:
            error(s)
        print "Update", u.getUsers()
        time.sleep(.1)


    
