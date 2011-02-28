#! /usr/bin/python

# Python ctypes bindings for OpenNI
#
# Copyright (C) 2011 Olivier Aubert
#
# Authors: Olivier Aubert <olivier.aubert at liris.cnrs.fr>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston MA 02110-1301, USA.

"""This module provides bindings for the OpenNI C API.
"""

import ctypes
import sys

build_date  = ''  # build time stamp and __version__, see generate.py

 # Used on win32 and MacOS in override.py
plugin_path = None

if sys.platform.startswith('linux'):
    dll = ctypes.CDLL('libOpenNI.so')

elif sys.platform.startswith('win'):
    import ctypes.util as u
    p = u.find_library('libopenni.dll')
    if p is None:
        dll = ctypes.CDLL('libvlc.dll')
    else:
        dll = ctypes.CDLL(p)
    del p

elif sys.platform.startswith('darwin'):
    dll = ctypes.CDLL('libOpenNI.dylib')

else:
    raise NotImplementedError('%s: %s not supported' % (sys.argv[0], sys.platform))

try:
    _Ints = (int, long)
except NameError:  # no long in Python 3+
    _Ints =  int

_Seqs = (list, tuple)

_Cfunctions = {}  # from LibVLC __version__

def _Cfunction(name, flags, *types):
    """(INTERNAL) New ctypes function binding.
    """
    if hasattr(dll, name):
        p = ctypes.CFUNCTYPE(*types)
        f = p((name, dll), flags)
        _Cfunctions[name] = f
        return f
    raise NameError('no function %r' % (name,))

def _Cobject(cls, ctype):
    """(INTERNAL) New instance from ctypes.
    """
    o = object.__new__(cls)
    o._as_parameter_ = ctype
    return o

def _Constructor(cls, ptr):
    """(INTERNAL) New wrapper from ctypes.
    """
    if ptr is None:
        raise Exception('(INTERNAL) ctypes class.')
    if ptr == 0:
        return None
    if not isinstance(ptr, ctypes.c_void_p):
        ptr = ctypes.c_void_p
    return _Cobject(cls, ptr)

class _Ctype(object):
    """(INTERNAL) Base class for ctypes.
    """
    @staticmethod
    def from_param(this):  # not self
        """(INTERNAL) ctypes parameter conversion method.
        """
        return this._as_parameter_

class ListPOINTER(object):
    """Just like a POINTER but accept a list of ctype as an argument.
    """
    def __init__(self, etype):
        self.etype = etype

    def from_param(self, param):
        if isinstance(param, _Seqs):
            return (self.etype * len(param))(*param)

class NodeHandleProxy(ctypes.c_void_p):
    def __OLDnew__(cls, *args):
        print "NEW code", args
        if args and args[0]:
            return NodeHandle(args[0])
        else:
            return ctypes.c_void_p()

class CALLBACK(ctypes.c_void_p):
    pass

 # Generated enum types #
# GENERATED_ENUMS go here  # see generate.py
 # End of generated enum types #

 # From libvlc_structures.h
# GENERATED_STRUCTS go here # see generate.py
 # End of generated structs

 # End of header.py #

