
# Start of footer.py #

def debug_callback(event, *args, **kwds):
    '''Example callback, useful for debugging.
    '''
    l = ['event %s' % (event.type,)]
    if args:
        l.extend(map(str, args))
    if kwds:
        l.extend(sorted('%s=%s' % t for t in kwds.items()))
    print('Debug callback (%s)' % ', '.join(l))

if __name__ == '__main__':
    c = Context()
    err = EnumerationErrors()

    q=NodeQuery()
    q.SetCreationInfo("Foo")
    q.AddSupportedCapability("Mirror")
    output = MapOutputMode(640, 480, 30)
    q.AddSupportedMapOutputMode(output)    
    c.CreateDepthGenerator(q, err)
    
    u = c.CreateUserGenerator(q, err)
    if not u.IsCapabilitySupported('User::Skeleton'):
        raise "Unable to create UserGenerator"

    
