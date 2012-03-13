#! /usr/bin/python

import sys
import time
import ni

c = ni.Context("Config.xml")
#c = ni.Context('/home/oaubert/src/kinect/Nite-1.3.0.18/Data/Sample-User.xml')
if c is None:
    print "Cannot create context."
    sys.exit(0)

q = ni.NodeQuery()
err = ni.EnumerationErrors()

def debug(*p):
    print "DEBUG CB", str(p)

d = c.createDepthGenerator(q, err)
if not d:
    print "Error when creating depth generator"

u = c.createUserGenerator(q, err)
if not u.isCapabilitySupported(ni.Capability.SKELETON):
    raise "Unable to create UserGenerator"

h = u.registerUserCallbacks(ni.cb.UserHandler(debug), ni.cb.UserHandler(debug), "User")
print "Registered cb %x" % h

s=c.startGeneratingAll()
if s:
    ni.error(s)

print "Waiting"
for i in range(9):
    s = c.waitAndUpdateAll()
    if s:
        ni.error(s)
    print "Update", u.getUsers()
    time.sleep(.1)
