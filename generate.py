#! /usr/bin/python

# Code generator for openni ctypes bindings
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

"""This module parses OpenNI public C API include files and generates
corresponding Python/ctypes bindingsB{**} code.  Moreover, it
generates Python class and method wrappers from the OpenNI functions
and enum types.
"""
__all__     = ('Parser',
               'PythonGenerator',
               'process')
__version__ =  '20.11.02.25'

_debug = False

import sys
import os
import re
import time
import operator

# Opener for text files
if sys.hexversion < 0x3000000:
    def opener(name, mode='r'):
        return open(name, mode)
else:  # Python 3+
    def opener(name, mode='r'):  #PYCHOK expected
        return open(name, mode, encoding='utf8')

# Functions not wrapped/not referenced
_blacklist = {
}

# some constants
_NA_     = 'N/A'
_NL_     = '\n'  # os.linesep
_OUT_    = 'out]'
_PNTR_   = 'pointer to get the '  # KLUDGE: see @param ... [out]
_INDENT_ = '    '

# keywords in header files
_PUBLIC_API_  = 'XN_C_API'

# Precompiled regexps
api_re       = re.compile(_PUBLIC_API_ + '\s+(\S+\s+.+?)\s*\(\s*(.+?)\s*\)')
at_param_re  = re.compile('(@param\s+\S+)(.+)')
bs_param_re  = re.compile('\\param\s+(\S+)')
class_re     = re.compile('class\s+(\w+)(?:\(.+\))?:')
def_re       = re.compile('^\s+def\s+(\w+)', re.MULTILINE)
enum_re      = re.compile('(?:typedef\s+)?(enum)\s*(\S+)\s*\{\s*(.+)\s*\}\s*(?:\S+)?;')
enum_pair_re = re.compile('\s*=\s*')
enum_type_re = re.compile('^(?:typedef\s+)?enum')
struct_re    = re.compile('(?:typedef\s+)?(struct)\s*(\S+)\s*\{\s*(.+)\s*\}\s*(?:\S+)?;')
struct_type_re = re.compile('^(?:typedef\s+)?struct\s*(\w+)\s*$')
forward_re   = re.compile('.+\(\s*(.+?)\s*\)(\s*\S+)')
param_re     = re.compile('\s*(const\s*|unsigned\s*|struct\s*)?(\S+\s*\**)\s+(.+)')
paramlist_re = re.compile('\s*,\s*')
decllist_re  = re.compile('\s*;\s*')
typedef_re   = re.compile('^typedef\s+(?:struct\s+)?(\S+)\s+(\S+);')
version_re   = re.compile('\d+[.]\d+[.]\d+.*')
xncallback_re = re.compile('\(XN_CALLBACK_TYPE\*\s+(\S+)\)')
callbackdef_re = re.compile('typedef\s+(\w+)\s+\(XN_CALLBACK_TYPE\*\s+(\w+)\)\((.+)\);')
define_re    = re.compile('^#define\s+(XN_\S+)\s+(\S+)')

def endot(text):
    """Terminate string with a period.
    """
    if text and text[-1] not in '.,:;?!':
        text += '.'
    return text

def errorf(fmt, *args):
    """Print error.
    """
    global _nerrors
    _nerrors += 1
    print('Error: ' + fmt % args)

_nerrors = 0

def errors(fmt, e=0):
    """Report total number of errors.
    """
    if _nerrors > e:
        n = _nerrors - e
        x =  min(n, 9)
        errorf(fmt + '... exit(%s)', n, x)
        sys.exit(x)
    elif _debug:
        print(fmt % (_NL_ + 'No'))

class _Source(object):
    """Base class for elements parsed from source.
    """
    source = ''

    def __init__(self, file_='', line=0):
        self.source = '%s:%s' % (file_, line)
        self.dump()  #PYCHOK expected

class Enum(_Source):
    """Enum type.
    """
    type = 'enum'

    def __init__(self, name, type='enum', vals=(), docs='', **kwds):
        if type != self.type:
            raise TypeError('expected enum type: %s %s' % (type, name))
        self.docs = docs
        self.name = name
        self.vals = vals  # list/tuple of Val instances
        if _debug:
           _Source.__init__(self, **kwds)

    def check(self):
        """Perform some consistency checks.
        """
        if not self.docs:
            errorf('no comment for typedef %s %s', self.type, self.name)
        if self.type != 'enum':
            errorf('expected enum type: %s %s', self.type, self.name)

    def dump(self):  # for debug
        print('%s (%s): %s' % (self.name, self.type, self.source))
        for v in self.vals:
            v.dump()

    def epydocs(self):
        """Return epydoc string.
        """
        return self.docs.replace('@see', 'See').replace('\\see', 'See')

class Struct(_Source):
    """Struct type.
    """
    type = 'struct'

    def __init__(self, name, type='struct', fields=(), docs='', **kwds):
        if type != self.type:
            raise TypeError('expected struct type: %s %s' % (type, name))
        self.docs = docs
        self.name = name
        self.fields = fields  # list/tuple of Par instances
        if _debug:
           _Source.__init__(self, **kwds)

    def check(self):
        """Perform some consistency checks.
        """
        if not self.docs:
            errorf('no comment for typedef %s %s', self.type, self.name)
        if self.type != 'struct':
            errorf('expected struct type: %s %s', self.type, self.name)

    def dump(self):  # for debug
        print('%s (%s): %s' % (self.name, self.type, self.source))
        for v in self.fields:
            v.dump()

    def epydocs(self):
        """Return epydoc string.
        """
        return self.docs.replace('@see', 'See').replace('\\see', 'See')

class PrivateObject(_Source):
    """Private object
    """
    type = 'private'

    def __init__(self, name, type='private', docs='', **kwds):
        if type != self.type:
            raise TypeError('expected private type: %s %s' % (type, name))
        self.docs = docs
        self.name = name
        if _debug:
           _Source.__init__(self, **kwds)

    def dump(self):  # for debug
        print('%s (%s): %s' % (self.name, self.type, self.source))

class Flag(object):
    """Enum-like, ctypes parameter direction flag constants.
    """
    In     = 1  # input only
    Out    = 2  # output only
    InOut  = 3  # in- and output
    InZero = 4  # input, default int 0
    def __init__(self):
        raise TypeError('constants only')

class Func(_Source):
    """C function.
    """
    heads   = ()  # docs lines without most @tags
    out     = ()  # [out] parameter names
    params  = ()  # @param lines, except [out]
    tails   = ()  # @return, @version, @bug lines
    wrapped =  0  # number of times wrapped

    def __init__(self, name, type, pars=(), docs='', **kwds):
        self.docs = docs
        self.name = name
        self.pars = pars  # list/tuple of Par instances
        self.type = type
        if _debug:
           _Source.__init__(self, **kwds)

    def args(self, first=0):
        """Return the parameter names, excluding output parameters.
           Ctypes returns all output parameter values as part of
           the returned tuple.
        """
        return [p.name for p in self.pars[first:] if
                p.flags(self.out)[0] != Flag.Out]

    def check(self):
        """Perform some consistency checks.
        """
        if not self.docs:
            errorf('no comment for function %s', self.name)
        elif len(self.pars) != self.nparams:
            errorf('doc parameters (%d) mismatch for function %s (%d)',
                    self.nparams, self.name, len(self.pars))
            if _debug:
                self.dump()
                print(self.docs)

    def dump(self):  # for debug
        print('%s (%s): %s' %  (self.name, self.type, self.source))
        for p in self.pars:
            p.dump(self.out)

    def epydocs(self, first=0, indent=0):
        """Return epydoc doc string with/out first parameter.
        """
        # "out-of-bounds" slices are OK, e.g. ()[1:] == ()
        t = _NL_ + (' ' * indent)
        return t.join(self.heads + self.params[first:] + self.tails)

    def __nparams_(self):
        return (len(self.params) + len(self.out)) or len(bs_param_re.findall(self.docs))
    nparams = property(__nparams_, doc='number of \\param lines in doc string')

    def xform(self):
        """Transform Doxygen to epydoc syntax.
        """
        b, c, h, o, p, r, v = [], None, [], [], [], [], []
        # see <http://epydoc.sourceforge.net/manual-fields.html>
        # (or ...replace('{', 'E{lb}').replace('}', 'E{rb}') ?)
        for t in self.docs.replace('@{', '').replace('@}', '').replace('\\ingroup', '') \
                          .replace('{', '').replace('}', '') \
                          .replace('<b>', 'B{').replace('</b>', '}') \
                          .replace('@see', 'See').replace('\\see', 'See') \
                          .replace('\\bug', '@bug').replace('\\version', '@version') \
                          .replace('\\note', '@note').replace('\\warning', '@warning') \
                          .replace('\\param', '@param').replace('\\return', '@return') \
                          .splitlines():
            if '@param' in t:
                if _OUT_ in t:
                    # KLUDGE: remove @param, some comment and [out]
                    t = t.replace('@param', '').replace(_PNTR_, '').replace(_OUT_, '')
                    # keep parameter name and doc string
                    o.append(' '.join(t.split()))
                    c = ['']  # drop continuation line(s)
                else:
                    p.append(at_param_re.sub('\\1:\\2', t))
                    c = p
            elif '@return' in t:
                r.append(t.replace('@return ', '@return: '))
                c = r
            elif '@bug' in t:
                b.append(t.replace('@bug ', '@bug: '))
                c = b
            elif '@version' in t:
                v.append(t.replace('@version ', '@version: '))
                c = v
            elif c is None:
                h.append(t.replace('@note ', '@note: ').replace('@warning ', '@warning: '))
            else:  # continuation, concatenate to previous @tag line
                c[-1] = '%s %s' % (c[-1], t.strip())
        if h:
            h[-1] = endot(h[-1])
            self.heads = tuple(h)
        if o:  # just the [out] parameter names
            self.out = tuple(t.split()[0] for t in o)
            # ctypes returns [out] parameters as tuple
            r = ['@return: %s' % ', '.join(o)]
        if p:
            self.params = tuple(map(endot, p))
        t = r + v + b
        if t:
            self.tails = tuple(map(endot, t))

class Par(object):
    """C function parameter.
    """
    def __init__(self, name, type):
        self.name = name
        self.type = type  # C type

    def dump(self, out=()):  # for debug
        if self.name in out:
            t = _OUT_  # @param [out]
        else:
            t = {Flag.In:     '',  # default
                 Flag.Out:    'Out',
                 Flag.InOut:  'InOut',
                 Flag.InZero: 'InZero',
                }.get(self.flags()[0], 'FIXME_Flag')
        print('%s%s (%s) %s' % (_INDENT_, self.name, self.type, t))

    def isIn(self):
        return self.flags()[0] & Flag.In

    def isOut(self):
        return self.flags()[0] & Flag.Out
            
    # Parameter passing flags for types.  This shouldn't
    # be hardcoded this way, but works all right for now.
    def flags(self, out=(), default=None):
        """Return parameter flags tuple.

        Return the parameter flags tuple for the given parameter
        type and name and a list of parameter names documented as
        [out].
        """
        if self.name in out:
            f = Flag.Out  # @param [out]
        else:
            f = {'int*':      Flag.Out,
                 'unsigned*': Flag.Out,
                 'XnEnumerationErrors*': Flag.Out,
                }.get(self.type, Flag.In)  # default
        if default is None:
            return f,  # 1-tuple
        else:  # see ctypes 15.16.2.4 Function prototypes
            return f, self.name, default  #PYCHOK expected

class Val(object):
    """Enum name and value.
    """
    def __init__(self, enum, value):
        self.enum = enum  # C name
        # convert name
        t = enum.split('_')
        n = t[-1]
        if len(n) <= 1:  # single char name
            n = '_'.join( t[-2:] )  # some use 1_1, 5_1, etc.
        if n[0].isdigit():  # can't start with a number
            n = '_' + n
        self.name = n
        self.value = value

    def dump(self):  # for debug
        print('%s%s = %s' % (_INDENT_, self.name, self.value))

class Parser(object):
    """Parser of C header files.
    """
    h_file = ''

    def __init__(self, h_files, version=''):
        self.enums = []
        self.funcs = []
        self.structs = []
        self.privates = []
        self.callbacks = []
        # Meaningful defines
        self.defines = {}

        self.typedefs = {}

        self.version = version

        for h in h_files:
            self.h_file = h
            self.typedefs.update(self.parse_typedefs())
            self.enums.extend(self.parse_enums())
            self.funcs.extend(self.parse_funcs())
            self.structs.extend(self.parse_structs())
            self.callbacks.extend(self.parse_callbacks())
            self.defines.update(self.parse_defines())

        # Handle private structs
        for new, original in self.typedefs.iteritems():
           if new == original:
               # Private object. Create an empty Class.
               self.privates.append(PrivateObject(new, 'private'))

    def check(self):
        """Perform some consistency checks.
        """
        for e in self.enums:
            e.check()
        for f in self.funcs:
            f.check()
        for s in self.structs:
            s.check()

    def __dump(self, attr):
        print('%s==== %s ==== %s' % (_NL_, attr, self.version))
        for a in getattr(self, attr, ()):
            a.dump()

    def dump_enums(self):  # for debug
        self.__dump('enums')

    def dump_structs(self):  # for debug
        self.__dump('structs')

    def dump_funcs(self):  # for debug
        self.__dump('funcs')

    def dump_privates(self):  # for debug
        self.__dump('privates')

    def dump_callbacks(self):  # for debug
        self.__dump('callbacks')
    
    def dump_defines(self):
        print('\n=== defines ====')
        for k in sorted(self.defines):
            print "  %s = %s" % (k, self.defines[k])
        
    def parse_enums(self):
        """Parse header file for enum type definitions.

        @return: yield an Enum instance for each enum.
        """
        for typ, name, enum, docs, line in self.parse_groups(enum_type_re.match, enum_re.match):
            vals, v = [], -1  # enum value(s)
            for t in paramlist_re.split(enum):
                t = t.strip()
                if not t.startswith('/*'):
                    if '=' in t:  # has value
                        n, v = enum_pair_re.split(t)
                        vals.append(Val(n, v))
                        if v.startswith('0x'):  # '0X'?
                            v = int(v, 16)
                        else:
                            v = int(v)
                    elif t:  # only name
                        v += 1
                        vals.append(Val(t, str(v)))

            name = name.strip()
            if not name:  # anonymous?
                name = 'FIXME'

            # more doc string cleanup
            docs = endot(docs).capitalize()

            yield Enum(name, typ, vals, docs,
                       file_=self.h_file, line=line)

    def parse_structs(self):
        """Parse header file for struct definitions.

        @return: yield a Struct instance for each struct.
        """
        for typ, name, body, docs, line in self.parse_groups(struct_type_re.match, struct_re.match, '^\}(\s+\S+)?;$'):
            fields = [ self.parse_param(t) for t in decllist_re.split(body) if not '%s()' % name in t ]
            fields = [ f for f in fields if f is not None ]

            name = name.strip()
            if not name:  # anonymous?
                name = 'FIXME_undefined_name'

            # more doc string cleanup
            docs = endot(docs).capitalize()

            yield Struct(name, typ, fields, docs,
                         file_=self.h_file, line=line)

    def parse_funcs(self):
        """Parse header file for public function definitions.

        @return: yield a Func instance for each function, unless blacklisted.
        """
        def match_t(t):
            return t.startswith(_PUBLIC_API_) and not 'DEPRECATED' in t

        for name, pars, docs, line in self.parse_groups(match_t, api_re.match, '\);$'):

            f = self.parse_param(name)
            if f.name in _blacklist:
                _blacklist[f.name] = f.type
                continue

            pars = [self.parse_param(p) for p in paramlist_re.split(pars)]

            if len(pars) == 1 and pars[0].type == 'void':
                pars = []  # no parameters
                
            missing = [ p for p in pars if not p.name ]
            if missing:
                print "Missing parameter", p.type
                continue

            yield Func(f.name, f.type, pars, docs,
                       file_=self.h_file, line=line)

    def parse_typedefs(self):
        """Parse header file for typedef definitions.

        @return: a dict instance with typedef matches
        """
        return dict( (new, original) 
            for original, new, docs, line in self.parse_groups(typedef_re.match, typedef_re.match) )

    def parse_defines(self):
        """Parse header file for useful defines

        @return: a dict instance with defines
        """
        res = {}
        f = opener(self.h_file)
        for l in f:
            m = define_re.search(l)
            if m:
                res[m.group(1)] = m.group(2)
        f.close()
        return res

    def parse_callbacks(self):
        """Parse header file for callback signature definitions.

        @return: Yield a Func for each callback
        """
        for rettype, name, pars, docs, line in self.parse_groups(callbackdef_re.match, callbackdef_re.match, '\);$'):

            f = self.parse_param(name)
            pars = [self.parse_param(p) for p in paramlist_re.split(pars)]

            if len(pars) == 1 and pars[0].type == 'void':
                pars = []  # no parameters
                
            missing = [ p for p in pars if not p.name ]
            if missing:
                print "Missing parameter", p.type
                continue

            yield Func(name, rettype, pars, docs,
                       file_=self.h_file, line=line)

    def parse_groups(self, match_t, match_re, end_block_re=';$'):
        """Parse header file for matching lines, re and ends.

        @return: yield a tuple of re groups extended with the
        doc string and the line number in the header file.
        """
        a = []  # multi-lines
        d = []  # doc lines
        n = 0   # line number
        s = False  # skip comments except doc
        ends = re.compile(end_block_re)

        f = opener(self.h_file)
        for t in f:
            n += 1
            # collect doc lines
            if t.startswith('/**'):
                d =     [t[3:].rstrip()]
            elif t.startswith(' * '):  # FIXME: keep empty lines
                d.append(t[3:].rstrip())
            elif t.startswith('#'):
                # preprocessor directive. FIXME: handle?
                continue
            else:  # parse line
                if '//' in t:
                    t = t[:t.index('//')]
                t, m = t.strip(), None
                if s or t.startswith('/*'):  # in comment
                    s = not t.endswith('*/')

                elif a:  # accumulate multi-line
                    t = t.split('/*', 1)[0].rstrip()  # //?
                    a.append(t)
                    if ends.search(t):
                        t = ' '.join(a)
                        m = match_re(t)
                        #print "----------------------- BLOCK -----------------"
                        #print "\n".join(a)
                        #print "-----------------------------------------------"
                        a = []
                elif match_t(t):
                    if ends.search(t):
                        m = match_re(t)  # single line
                    else:  # new multi-line
                        a = [t]

                if m:
                    # clean up doc string
                    d = _NL_.join(d).strip()
                    if d.endswith('*/'):
                        d = d[:-2].rstrip()

                    if _debug:
                        print('%s==== source ==== %s:%d' % (_NL_, self.h_file, n))
                        print(t)
                        print('"""%s%s"""' % (d, _NL_))

                    yield m.groups() + (d, n)
                    d = []
        f.close()

    def parse_param(self, param):
        """Parse a C parameter expression.

        It is used to parse the type/name of functions
        and type/name of the function parameters.

        @return: a Par instance.
        """
        param = param.strip()
        if param.startswith('}'):
            # Leftover from structs with constructors.
            param = param[1:].strip()
        if not param: 
            return None
        if '{' in param:
            # Cannot parse this.
            return None
        t = param.replace('const', '').strip()
        #if _*_FORWARD_ in t:
        #    m = forward_re.match(t)
        #    t = m.group(1) + m.group(2)

        m = param_re.search(t)
        if m:
            _, t, n = m.groups()
            while n.startswith('*'):
                n  = n[1:].lstrip()
                t += '*'
##          if n == 'const*':
##              # K&R: [const] char* const*
##              n = ''
        else:  # K&R: only [const] type
            n = ''

        m = xncallback_re.search(n)
        if m:
            # It is a callback method. Use a generic mapping for now.
            # FIXME: should generate appropriate callback sigs
            n = m.group(1)
            t = 'CALLBACK'

        t = t.replace(' ', '')
        if t == '...':
            # varargs spec
            n = 'varargs'

        if '[' in n:
            n = n[:n.index('[')]
            t += '*'

        return Par(n, t.strip())


class _Generator(object):
    """Base class.
    """
    comment_line = '#'   # Python
    file         = None
    links        = {}    # must be overloaded
    outdir       = ''
    outpath      = ''
    type_re      = None  # must be overloaded
    type2class   = {}    # must be overloaded

    def __init__(self, parser=None):
      ##self.type2class = self.type2class.copy()
        self.parser = parser
        self.convert_classnames('enum')
        self.convert_classnames('struct')
        self.convert_classnames('private')
        self.convert_classnames('callback')

    def check_types(self):
        """Make sure that all types are properly translated.

        @note: This method must be called B{after} C{convert_classnames},
        since the latter populates C{type2class} with enum class names.
        """
        e = _nerrors
        for f in self.parser.funcs:
            if f.type not in self.type2class:
                errorf('no type conversion for %s %s (%s)', f.type, f.name, f.source)
            for p in f.pars:
                if p.type not in self.type2class:
                    errorf('no type conversion for %s %s in %s (%s)', p.type, p.name, f.name, f.source)
        errors('%s type conversion(s) missing', e)

    def class4(self, c_name):
        """Return the class name for a type or enum.
        """
        return self.type2class.get(c_name, '') or ('FIXME_%s' % (c_name,))

    def convert_classnames(self, source):
        """Convert enum names to class names.
        
        source is either 'enum' or 'struct'.

        """
        for e in getattr(self.parser, source+'s'):
            if e.name in self.type2class:
                # Do not override predefined values
                continue

            c = self.type_re.findall(e.name)
            if c:
                c = c[0]
            else:
                c = e.name
            if '_' in c:
                c = c.title().replace('_', '')
            elif c[0].islower():
                c = c.capitalize()
            self.type2class[e.name] = c

    def dump_dicts(self):  # for debug
        s = _NL_ + _INDENT_
        for n in ('type2class', 'prefixes', 'links'):
            d = getattr(self, n, None)
            if d:
                n = ['%s==== %s ==== %s' % (_NL_, n, self.parser.version)]
                print(s.join(n + sorted('%s: %s' % t for t in d.items())))

    def epylink(self, docs, striprefix=None):
        """Link function, method and type names in doc string.
        """
        if striprefix:
            return striprefix(docs)
        else:
            return docs

    def generate_enums(self):
        raise TypeError('must be overloaded')

    def insert_code(self, source, genums=False):
        """Include code from source file.
        """
        f = opener(source)
        for t in f:
            if genums and t.startswith('# GENERATED_ENUMS'):
                self.generate_defines()
                self.generate_enums()
            elif genums and t.startswith('# GENERATED_STRUCTS'):
                #self.generate_privates()
                self.generate_structs()
            elif t.startswith("build_date ="):
                v, t = _NA_, self.parser.version
                if t:
                    v, t = t, ' ' + t
                self.output('__version__ = "%s"' % (v,))
                self.output('build_date = "%s%s"' % (time.ctime(), t))
            else:
                self.output(t, nt=0)
        f.close()

    def outclose(self):
        """Close the output file.
        """
        if self.file not in (None, sys.stdout):
           self.file.close()
        self.file = None

    def outopen(self, name):
        """Open an output file.
        """
        if self.file:
            self.outclose()
            raise IOError('file left open: %s' % (self.outpath,))

        if name in ('-', 'stdout'):
            self.outpath = 'stdout'
            self.file = sys.stdout
        else:
            self.outpath = os.path.join(self.outdir, name)
            self.file = opener(self.outpath, 'w')

    def output(self, text, nl=0, nt=1):
        """Write to current output file.
        """
        if nl:  # leading newlines
            self.file.write(_NL_ * nl)
        self.file.write(text)
        if nt:  # trailing newlines
            self.file.write(_NL_ * nt)

    def unwrapped(self):
        """Report the unwrapped and blacklisted functions.
        """
        b = [f for f, t in _blacklist.items() if t]
        u = ["%s (%s)" % (f.name, (f.pars and self.class4(f.pars[0].type)) or "None") for f in self.parser.funcs if not f.wrapped]
        c = self.comment_line
        for f, t in ((b, 'blacklisted'),
                     (u, 'not wrapped as methods')):
            if f:
                self.output('%s %d function(s) %s:' % (c, len(f), t), nl=1)
                self.output(_NL_.join('%s  %s' % (c, f) for f in sorted(f)))  #PYCHOK false?


class PythonGenerator(_Generator):
    """Generate Python bindings.
    """
    type_re = re.compile('Xn(.+?)$')  # Python

    # C-type to Python/ctypes type conversion.  Note, enum
    # type conversions are generated (cf convert_enums).
    type2class = {
        # Internal classes
        'XnContext*': 'Context',
        'XnContext**': 'ctypes.POINTER(ContextReference)',

        'XnModuleInstance*': 'ctypes.c_void_p',
        'XN_THREAD_ID': 'ctypes.c_void_p',
        'XnNeededNodesDataHash*': 'ctypes.c_void_p',
        'XnModuleStateCookieHash*': 'ctypes.c_void_p',
        'XnLicenseList*': 'ctypes.c_void_p',
        'XnModuleLoader*': 'ctypes.c_void_p',
        'XnNodesMap*': 'ctypes.c_void_p',
        'XnErrorStateChangedEvent*': 'ctypes.c_void_p',
        'XN_EVENT_HANDLE': 'ctypes.c_void_p',

        'XnFPSData': 'FPSData',

        #'XnLockData': 'LockData',
        #'XnGestureRecognizedParams': 'GestureRecognizedParams',
        #'XnGestureProgressParams': 'GestureProgressParams',

        'XnNodeInfo*': 'NodeInfo',
        'XnNodeInfoListNode*': 'NodeInfoListNode',
        #'XnNodeInfoListNode*': 'ctypes.c_void_p',

        'XnNodeInfoList*': 'NodeInfoList', 
        'XnNodeInfoList**': 'ctypes.POINTER(NodeInfoListReference)', 

        #'XnNeededNodeData': 'NeededNodeData',
        'XnNodeQuery*': 'NodeQuery',
        'XnNodeQuery**': 'ctypes.POINTER(NodeQuery)',

        'XnEnumerationErrors*': 'EnumerationErrors',
        'XnEnumerationErrors**': 'ctypes.POINTER(EnumerationErrors)',
        'XnEnumerationErrorsIterator': 'EnumerationErrorsIterator',

        'XnProductionNodeType*': 'ctypes.POINTER(XnProductionNodeType)',
        'XnPixelFormat*': 'ctypes.POINTER(PixelFormat)',

        'XnNodeHandle': 'NodeHandle',
        'XnNodeHandle*': 'ctypes.POINTER(NodeHandle)',

        'XnSkeletonJoint*': 'ctypes.POINTER(SkeletonJoint)',
        'XnRecordMedium*': 'ctypes.POINTER(RecordMedium)',

        'XnPoseDetectionStatus*': 'ctypes.POINTER(XnPoseDetectionStatus)',
        'XnPoseDetectionState*': 'ctypes.POINTER(XnPoseDetectionState)',

        'XnSizeT': 'ctypes.c_ulong',
        'CALLBACK': 'ctypes.c_void_p',

        'timespec*':    'FIXME',
        'va_list':    'FIXME',

        'XnStatus':     'ctypes.c_uint32',
        'XnBool':       'ctypes.c_uint',
        'XnBool*':      'ctypes.POINTER(ctypes.c_uint)',
        'XnChar':       'ctypes.c_char',
        'XnChar*':      'ctypes.c_char_p',
        'XnChar**':     'ListPOINTER(ctypes.c_char_p)',
        'XnDouble':     'ctypes.c_double',
        'XnDouble*':    'ctypes.POINTER(ctypes.c_double)',
        'XnFloat':      'ctypes.c_float',
        'XnFloat*':     'ctypes.POINTER(ctypes.c_float)',
        'XnInt32':      'ctypes.c_int32',
        'XnInt32*':     'ctypes.POINTER(ctypes.c_int32)',
        'XnInt64':      'ctypes.c_int64',
        'XnInt64*':      'ctypes.POINTER(ctypes.c_int64)',
        'XnUChar*':     'ctypes.POINTER(ctypes.c_ubyte)',
        'XnUInt':       'ctypes.c_uint',
        'XnUInt*':      'ctypes.POINTER(ctypes.c_uint)',
        'XnUInt16':     'ctypes.c_uint16',
        'XnUInt16*':    'ctypes.POINTER(ctypes.c_uint16)',
        'XnUInt32':     'ctypes.c_uint32',
        'XnUInt32*':    'ctypes.POINTER(ctypes.c_uint32)',
        'XnUInt64':     'ctypes.c_uint64',
        'XnUInt64*':    'ctypes.POINTER(ctypes.c_uint64)',
        'XnUInt8':      'ctypes.c_uint8',
        'XnUInt8*':     'ctypes.POINTER(ctypes.c_uint8)',
        
        '...':       'FIXME_va_list',
        'char*':     'ctypes.c_char_p',
        'char**':    'ListPOINTER(ctypes.c_char_p)',
        'float':     'ctypes.c_float',
        'int':       'ctypes.c_int',
        'int*':      'ctypes.POINTER(ctypes.c_int)',  # _video_get_cursor
        'int64_t':   'ctypes.c_int64',
        'short':     'ctypes.c_short',
        'uint32_t':  'ctypes.c_uint32',
        'unsigned':  'ctypes.c_uint',
        'unsigned*': 'ctypes.POINTER(ctypes.c_uint)',  # _video_get_size
        'void':      'None',
        'void*':     'ctypes.c_void_p',
        'void**':    'ListPOINTER(ctypes.c_void_p)',
        'WINDOWHANDLE': 'ctypes.c_ulong',
    }

    # Python classes, i.e. classes for which we want to
    # generate class wrappers around some functions
    defined_classes = (
        'Context',
        'NodeHandle',
        'NodeQuery',
        'EnumerationErrors',
        'NodeInfoList',
        'NodeInfo',
    )

    def __init__(self, parser=None):
        """New instance.

        @param parser: a L{Parser} instance.
        """
        # Load override definitions
        self.overrides = self.parse_override('override.py')

        _Generator.__init__(self, parser)

        # Generate conversions for typedefs other than private structs
        for new, original in parser.typedefs.iteritems():
            if original in self.type2class and not new in self.type2class:
                self.type2class[new] = self.type2class[original]
                self.type2class.setdefault(new+'*', 'ctypes.POINTER(%s)' % self.type2class[original])

        # Generate pointers type2class for structs
        for s in parser.structs:
            self.type2class.setdefault(s.name+'*', 'ctypes.POINTER(%s)' % self.type2class[s.name])

        # link enum value names to enum type/class
##      for t in self.parser.enums:
##          for v in t.vals:
##              self.links[v.enum] = t.name
        # prefixes to strip from method names
        # when wrapping them into class methods
        self.prefixes = {}
        for t, c in self.type2class.iteritems():
            t = t.rstrip('*')
            if c in self.defined_classes:
                self.links[t] = c
                self.prefixes[c] = t.replace('Xn', 'xn')
            elif c.startswith('ctypes.POINTER('):
                c = c.replace('ctypes.POINTER(', '') \
                     .rstrip(')')
                if c[:1].isupper():
                    self.links[t] = c
        # xform docs to epydoc lines
        for f in self.parser.funcs:
            f.xform()
            self.links[f.name] = f.name
        self.check_types()

    def generate_defines(self):
        """Generate classes for parsed defines.
        """
        for n in ('PROP', 'CAPABILITY'):
            prefix = 'XN_%s_' % n
            name = n.capitalize()
            data = "\n".join( "    %s = %s" % (k.replace(prefix, ''), 
                                               self.parser.defines[k])
                              for k in sorted(self.parser.defines)
                              if k.startswith(prefix) )
            self.output("""class %(name)s:
    '''%(prefix)s* constants
    '''
%(data)s
""" % locals())

    def generate_ctypes(self):
        """Generate a ctypes decorator for all functions.
        """
        self.output("""
 # Decorated C API functions #
""")
        for f in self.parser.funcs:
            name = f.name  #PYCHOK flake

            # arg names, excluding output args
            args = ', '.join(f.args())  #PYCHOK flake

            # tuples of arg flags
            flags = ', '.join(str(p.flags(f.out)) for p in f.pars)  #PYCHOK false?
            if flags:
                flags += ','

            # return value and arg classes
            types = ', '.join([self.class4(f.type)] +  #PYCHOK flake
                              [self.class4(p.type) for p in f.pars])

            # xformed doc string with first @param
            docs = self.epylink(f.epydocs(0, 4))  #PYCHOK flake
            self.output("""def %(name)s(%(args)s):
    '''%(docs)s
    '''
    f = _Cfunctions.get('%(name)s', None) or \\
        _Cfunction('%(name)s', (%(flags)s),
                    %(types)s)
    if not __debug__:  # i.e. python -O or -OO
        global %(name)s
        %(name)s = f
    return f(%(args)s)
""" % locals())

    def generate_callbacks(self):
        """Generate decorators for callback functions.
        
        We generate both decorators (for defining functions) and
        associated classes, to help in defining function signatures.
        """
        if not self.parser.callbacks:
            return
        # Generate classes
        for f in self.parser.callbacks:
            name = self.class4(f.name)  #PYCHOK flake
            docs = self.epylink(f.docs)
            self.output('''class %(name)s(ctypes.c_void_p):
    """%(docs)s
    """
    pass''' % locals())

        self.output("class CallbackDecorators(object):")
        self.output('    "Class holding various method decorators for callback functions."')
        for f in self.parser.callbacks:
            name = self.class4(f.name)  #PYCHOK flake

            # return value and arg classes
            types = ', '.join([self.class4(f.type)] +  #PYCHOK flake
                              [self.class4(p.type) for p in f.pars])

            # xformed doc string with first @param
            docs = self.epylink(f.docs)

            self.output("""    %(name)s = ctypes.CFUNCTYPE(%(types)s)
    %(name)s.__doc__ = '''%(docs)s
    '''""" % locals())
        self.output("cb = CallbackDecorators")

    def generate_enums(self):
        """Generate classes for all enum types.
        """
        self.output("""
class _Enum(ctypes.c_ulong):
    '''(INTERNAL) Base class
    '''
    _enum_names_ = {}

    def __str__(self):
        n = self._enum_names_.get(self.value, '') or ('FIXME_(%r)' % (self.value,))
        return '.'.join((self.__class__.__name__, n))

    def __repr__(self):
        return '.'.join((self.__class__.__module__, self.__str__()))

    def __eq__(self, other):
        return ( (isinstance(other, _Enum) and self.value == other.value)
              or (isinstance(other, _Ints) and self.value == other) )

    def __ne__(self, other):
        return not self.__eq__(other)
""")
        for e in self.parser.enums:

            cls = self.class4(e.name)
            self.output("""class %s(_Enum):
    '''%s
    '''
    _enum_names_ = {""" % (cls, e.epydocs() or _NA_))

            for v in e.vals:
                self.output("        %s: '%s'," % (v.value, v.name))
            self.output('    }')

            # align on '=' signs
            w = -max(len(v.name) for v in e.vals)
            t = ['%s.%*s = %s(%s)' % (cls, w,v.name, cls, v.value) for v in e.vals]

            self.output(_NL_.join(sorted(t)), nt=2)

    def generate_structs(self):
        """Generate classes for all structs types.
        """
        for e in self.parser.structs:
            cls = self.class4(e.name)
            if cls in self.overrides[1]:
                continue
            self.output("""class %s(ctypes.Structure):
    '''%s
    '''
    _fields_ = (""" % (cls, e.epydocs() or _NA_))

            for v in e.fields:
                self.output("        ('%s', %s)," % (v.name, self.class4(v.type).replace('Context', 'ContextReference').replace('NodeHandle', 'NodeHandleReference')))
            self.output('    )')
            self.output('')

    def generate_privates(self):
        """Generate classes for private objects.
        """
        #import pdb; pdb.set_trace()
        for e in self.parser.privates:
            cls = self.class4(e.name)
            if cls in self.overrides[1]:
                continue
            self.output("""class %s(ctypes.c_void_p):
    '''Private object
    '''
    pass
""" % cls)

    def generate_wrappers(self):
        """Generate class wrappers for all appropriate functions.
        """

        self.output("# START OF WRAPPED CLASSES")

        def striprefix(name):
            return name.replace(x, '').replace('xn', '')

        codes, methods, docstrs = self.overrides

        # sort functions on the type/class
        # of their first parameter
        t = []
        unwrapped_classes = set( self.defined_classes )
        for f in self.parser.funcs:
             if f.pars:
                 p = f.pars[0]
                 c = self.class4(p.type)
                 if c in self.defined_classes:
                     t.append((c, f))
                     unwrapped_classes.discard(c)

        # Wrap anonymous classes
        for c in unwrapped_classes:
            t.append( (c, None) )

        cls = x = ''  # wrap functions in class methods
        for c, f in sorted(t, key=operator.itemgetter(0)):
            if cls != c:
                cls = c
                self.output("""class %s(_Ctype):
    '''%s
    '''""" % (cls, docstrs.get(cls, '') or _NA_))

                c = codes.get(cls, '')
                if not 'def __new__' in c:
                    self.output("""
    def __new__(cls, ptr=None):
        '''(INTERNAL) ctypes wrapper constructor.
        '''
        return _Constructor(cls, ptr)
""")

                if c:
                    self.output(c)
                x = self.prefixes.get(cls, 'xn')

            if f is None:
                # Private objects
                continue
            f.wrapped += 1
            name = f.name

            # method name is function name less prefix
            meth = striprefix(name)
            # Lowercase first character
            meth = meth[0].lower() + meth[1:]
            if meth in methods.get(cls, []):
                continue  # overridden

            # arg names, excluding output args
            # and rename first arg to 'self'
            args = ', '.join(['self'] + f.args(1))  #PYCHOK flake

            # xformed doc string without first @param
            docs = self.epylink(f.epydocs(1, 8), striprefix)  #PYCHOK flake

            # Add a line with return types
            docs += "\nParameter types: " + ', '.join([self.class4(p.type) for p in f.pars])

            # FIXME: more generic ??
            #outparams = [ p for p in f.pars if p.isOut() ]

            # Hackish way to handle an opaque type (XnNodeHandle is an
            # opaque ctypes.POINTER(ctypes.c_void_p)).  Works for now,
            # something better should clearly be found: a list of
            # wrapped opaque types should be defined, and converted
            # through ctypes errcheck?
            references = [ self.class4(p.type) for p in f.pars if 'Reference' in self.class4(p.type) ]
            #print "REFERENCES", f.name, references
            if len(references) == 1:
                # We can convert to the appropriate type
                ref = re.findall('ctypes.POINTER\((.+)Reference\)', references[0])[0]
                self.output("""    def %(meth)s(%(args)s):
        '''%(docs)s
        '''
        return %(ref)s(%(name)s(%(args)s))
""" % locals())
            else:
                self.output("""    def %(meth)s(%(args)s):
        '''%(docs)s
        '''
        return %(name)s(%(args)s)
""" % locals())

    def parse_override(self, override):
        """Parse the override definitions file.

        It is possible to override methods definitions in classes.

        @param override: the C{override.py} file name.

        @return: a tuple (codes, methods, docstrs) of 3 dicts
        containing the source code, the method names and the
        class-level doc strings for each of the classes defined
        in the B{override} file.
        """
        codes = {}
        k, v = None, []
        f = opener(override)
        for t in f:
            m = class_re.match(t)
            if m:  # new class
                if k is not None:
                    codes[k] = ''.join(v)
                k, v = m.group(1), []
            else:
                v.append(t)
        if k is not None:
            codes[k] = ''.join(v)
        f.close()

        docstrs, methods = {}, {}
        for k, v in codes.items():
            q = v.lstrip()[:3]
            if q in ('"""', "'''"):
                # use class comment as doc string
                _, docstrs[k], v = v.split(q, 2)
                codes[k] = v
            # FIXME: not robust wrt. internal methods
            methods[k] = def_re.findall(v)

        return codes, methods, docstrs

    def save(self, path=None):
        """Write Python bindings to a file or C{stdout}.
        """
        self.outopen(path or '-')
        self.insert_code('header.py', genums=True)

        self.generate_wrappers()
        self.generate_ctypes()
        self.generate_callbacks()

        self.unwrapped()

        self.insert_code('footer.py')
        self.outclose()

def process(output, h_files):
    """Generate Python bindings.
    """
    p = Parser(h_files)
    g = PythonGenerator(p)
    g.save(output)


if __name__ == '__main__':

    from optparse import OptionParser

    opt = OptionParser(usage="""%prog  [options]  <include_directory> | <include_file.h> [...]

Parse include files and generate bindings code for Python.""")

    opt.add_option('-c', '--check', dest='check', action='store_true',
                   default=False,
                   help='Check mode, generates no bindings')

    opt.add_option('-d', '--debug', dest='debug', action='store_true',
                   default=False,
                   help='Debug mode, generate no bindings')

    opt.add_option('-s', '--structs', dest='structs', action='store_true',
                   default=False,
                   help='Dump structure definitions')

    opt.add_option('-o', '--output', dest='output', action='store', type='str',
                   default='-',
                   help='Output filename (for Python) or directory (for Java)')

    opt.add_option('-v', '--version', dest='version', action='store', type='str',
                   default='',
                   help='Version string for __version__ global')

    opts, args = opt.parse_args()

    if '--debug' in sys.argv:
       _debug = True  # show source

    if not args:
        opt.print_help()
        sys.exit(1)

    elif len(args) == 1:  # get .h files
        # get .h files from .../include dir
        # or .../include/*.h (especially
        # useful on Windows, where cmd does
        # not provide wildcard expansion)
        p = args[0]
        if os.path.isdir(p):
            p = os.path.join(p, '*.h')
        import glob
        args = glob.glob(p)

    p = Parser(args, opts.version)
    if opts.debug:
        p.dump_enums()
        p.dump_structs()
        p.dump_funcs()
        p.dump_privates()
        p.dump_defines()
        p.dump_callbacks()

    if opts.check:
        p.check()
        ty = set( p.type for f in p.funcs for p in f.pars )

        print "===========INSTANCES============="
        for n in sorted(set( f.pars[0].type for f in p.funcs if f.pars )):
            print n
        
        #ty = ty.union( p.type for f in p.structs for p in f.fields )
        #print "TYPEDEFS"
        #for n, o in p.typedefs.iteritems():
        #    print n, "\t", o

    else:
        g = PythonGenerator(p)
        if opts.debug:
            g.dump_dicts()
        elif opts.structs:
            g.outopen(opts.output)
            g.output('import ctypes')
            g.generate_enums()
            g.generate_structs()
        elif not _nerrors:
            g.save(opts.output)

    errors('%s error(s) reported')
