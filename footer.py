
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
    pass
