ctypes-based python bindings for OpenNI
=======================================

This repository contains a bindings generator for OpenNI. The
generate.py script parses the OpenNI include files, more specifically
the XN_C_API marked functions, and wraps them using ctypes.

Moreover, object-oriented wrappers are generated to provide a more
pythonic experience.

Note: for the moment, not all base types are defined in the bindings
generator. Hence, it will be unable to generate bindings for all .h
files, but only for a subset. See the Makefile INCLUDES variable to see
the currently supported includes.
