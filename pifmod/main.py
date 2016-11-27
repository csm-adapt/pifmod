#!/usr/bin/env python
"""
DESCRIPTION

    TODO This describes how to use this script. This docstring
    will be printed by the script if there is an error or
    if the user requests help (-h or --help).

EXAMPLES

    TODO: Show some examples of how to use this script.
"""

import sys, os, textwrap, traceback, argparse
import time
import shutil
import re
import ast
import json
from StringIO import StringIO
#from pexpect import run, spawn
from pypif import pif
from pypif.pif import Property, Value, Person
#
from pifmod.linkages import sagittariidae

# exceptions
class LocalException(Exception):
    def __init__(self, *args, **kwds):
        super(LocalException, self).__init__(self, *args, **kwds)
#end 'class LocalException(Exception):'

class EntryExistsError(LocalException):
    def __init__(self, *args, **kwds):
        super(EntryExistsError, self).__init__(*args, **kwds)
#end 'class EntryExistsError(Exception):'

class UnrecognizedOptionValueError(LocalException):
    def __init__(self, *args, **kwds):
        super(UnrecognizedOptionValueError, self).__init__(self, *args, **kwds)
#end 'class UnrecognizedOptionValueError(Exception):'


# authorize overwrite
def file_exists(filename):
    """
    Returns True if the file exists, False otherwise
    """
    try:
        open(filename).close()
        return True
    except IOError:
        return False


def authorize_overwrite(filename):
    """
    Returns True if FILENAME should be overwritten, False otherwise.
    """
    if file_exists(filename) and not args.force:
        msg = "{} exists. Overwrite? (y/N): ".format(filename)
        ans = raw_input(msg).strip()
        try:
            # answer was Yes, yes, yeah, etc. -- anything starting with 'y'
            if ans[0] in ('y', 'Y'):
                return True
        except IndexError:
            pass
        return False
    return True


# check tag
def check_tag(pifdata, tag):
    """
    Check if the tag exists and is not None.

    Parameters
    ----------
    :pifdata, PIF: File data read in using pif.load.
    :tag, str: name of the tag

    Out
    ---
    True, if tag is present and not None; False, otherwise.
    """
    return getattr(pifdata, tag, None) is not None


# property
def property(pifdata):
    """
    Gets/sets a property in the PIF-formatted data. There are several
    anticipated use cases:

        1. pifmod -i material.pif property NAME
            # This returns the Property named NAME, if it exists.

        2. pifmod -i material.pif property --units=mm NAME=VALUE
            # Create a *new* Property named NAME with value VALUE.
            # VALUE can take the form of a scalar (string or number);
            # a 1D list (vector), e.g. [1, 2, 3] or ['a', 'b', 'c']; or
            # a 2D list of lists (matrix), e.g. [[1, 2, 3], [4, 5, 6]].
            # Note that this will not overwrite an existing property with
            # the same name. For that, see use case #3. Select Property
            # keywords may be passed as options, e.g.
            #   --condition="KEY=VALUE[=UNITS]"
            #       Creates a new Value object named KEY with value
            #       VALUE and optional UNITS. Multiple conditions may be
            #       specified.
            #   --data-type={MACHINE_LEARNING|COMPUTATIONAL|EXPERIMENTAL}
            #       Sets the type of data the makes up this Property.
            # START HERE -- describe how to parse name: last,first=email then
            #            -- implement
            #   --contact="NAME[=EMAIL]"
            #       Person to contact, with optional email, for more
            #       information on this property. Multiple contacts may be
            #       specified. NAME can be "GIVEN FAMILY" or "GIVEN", but
            #       should not include prefixes, suffixes, etc. GIVEN names
            #       with spaces will not parse correctly.
            #   --tag="TAG"
            #       Any string TAG stored alongside the data. Multiple tags
            #       may be specified.

        3. pifmod -i material.pif property -f --units=mm PROPERTY=VALUE
            # As above, but if the property already exists, it will be
            # overwritten.

        4. pifmod -i material.pif property [-f] PIF NAME
            # Extracts a property from the PIF-formatted file PIF named
            # NAME and adds it to material.pif. If the force flag (-f) is
            # specified, an existing property will be overwritten.

        5. pifmod -i material.pif property --list [PIF]
            # Lists the property names in material.pif and, if specified,
            # in the PIF-formatted PIF file as well. Note that this only
            # lists the keys and not the values.

    Parameters
    ----------
    :pifdata, PIF: PIF-formatted data.

    Returns
    -------
    Use case:
        1. Matching property as a PIF Property
        2-4. pifdata string with Property added as appropriate.
    """
    def get_property(plist, name, case_sensitive=False):
        """Returns the first property whose name matches NAME."""
        #plist = pdata.properties if pdata.properties else []
        name = name if case_sensitive else name.lower()
        for prop in plist:
            nom = prop.name if case_sensitive else prop.name.lower()
            if nom == name:
                return prop
        return None
    def property_adder(plist, prop_exists):
        """
        Generator that abstracts away how new properties are added to an
        existing property list.
        """
        def no_conflict(padd):
            plist.append(padd)
        def conflict(padd):
            if args.force:
                for i,entry in enumerate(plist):
                    if entry.name == padd.name:
                        plist[i] = padd
                        return
            else:
                # Do not overwrite.
                msg = 'A property named "{}" already exists.'.format(padd.name)
                raise EntryExistsError(msg)
        return conflict if prop_exists else no_conflict
    def infer_value(vstr):
        """
        Infer whether the value string is a scalar, vector, or
        matrix.

            scalars: single value
            vectors: one or more scalars in square brackets, e.g. [1, 2, 3]
            matrices: vector of vectors (row-dominant).

        Returns
        -------
            (value type, value)
        """
        # ensure all character strings are quoted, otherwise they will
        # be treated as variables and raise an Exception
        quoteRE = re.compile(r"""(\b[a-zA-Z_]\w*)""")
        vstr = re.sub(quoteRE, r'"\1"', str(vstr))
        # do not use the built in eval as this is a huge security
        # vulnerability. ast.literal_eval only allows evaluation to
        # basic types, lists, tuples, dicts and None.
        value = ast.literal_eval(vstr)
        if not isinstance(value, list):
            # is value a scalar?
            return ('scalars', value)
        elif not isinstance(value[0], list):
            # is value a list of scalars, e.g. vector?
            return ('vectors', value)
        else:
            # value must be a vector of vectors
            return ('matrices', value)
    def parse_units(units):
        return units
    def parse_condition(cond):
        kwds = {}
        if cond is None:
            return None
        try:
            k,v,u = cond.strip().split('=')
            kwds['units'] = u
        except ValueError:
            k,v = cond.strip().split('=')
        vtype, v = infer_value(v)
        kwds['name'] = k
        kwds[vtype] = v
        return Value(**kwds)
    def parse_data_type(dtype):
        allowedRE = re.compile(r'(MACHINE_LEARNING|COMPUTATIONAL|EXPERIMENTAL)',
                               re.IGNORECASE)
        if dtype is None:
            return None
        elif re.match(allowedRE, dtype):
            return dtype
        else:
            msg = 'Data type must be one of: MACHINE_LEARNING, ' \
                  'COMPUTATIONAL, or EXPERIMENTAL.'
            UnrecognizedOptionValueError(msg)
    def parse_contact(cont):
        kwds = {}
        if cont is None:
            return None
        # split name and email
        try:
            name,email = cont.strip().split(',')
            kwds['email'] = email.strip()
        except ValueError:
            name = cont.strip()
        # split given name from family name
        try:
            name = name.split()
            given = name[0]
            family = ' '.join(name[1:])
        except ValueError:
            given = name.strip()
            family = None
        kwds['given'] = given
        kwds['family'] = family
        return Person(**kwds)
    def parse_tag(tag):
        return tag
    def parse_json(filename):
        # which key/keys are equivalent to scalar values?
        valueRE = re.compile(r'value.*?\b', re.IGNORECASE)
        # TODO: which key/keys are equivalent to vectors? matrices?
        # load the json file
        with open(filename) as ifs:
            jdata = json.load(ifs)
        # create an empty list of properties
        props = []
        for k,v in iter(jdata.items()):
            try:
                # if v is a dictionary, i.e. has
                # [scalar/vector/matrix equivalent][, units[, ...]]
                # create a Property from this data.
                for key in v.keys():
                    if re.match(valueRE, key):
                        vtype, val = infer_value(v[key])
                        v[vtype] = v[key]
                        del v[key]
                prop = Property(k, **v)
            except AttributeError:
                # list, scalar, etc. -- something that doesn't have the
                # map defining the characteristics of the entry.
                vtype, val = infer_value(v)
                kwds = { vtype : val }
                prop = Property(k, **kwds)
            props.append(prop)
        return props
    # parse command line options
    if pifdata.properties is None:
        pifdata.properties = []
    proplist = pifdata.properties
    # only list the available property names
    if args.list:
        ostream = StringIO()
        ostream.write("PIF data\n")
        for prop in proplist:
            ostream.write("- {}\n".format(prop.name))
        try:
            properties = args.arglist[0]
            properties = parse_json(properties)
            ostream.write("{}\n".format(args.arglist[0]))
            for prop in properties:
                ostream.write("- {}\n".format(prop.name))
        except IndexError:
            pass
        result = ostream.getvalue()
        ostream.close()
        return result
    nargs = len(args.arglist)
    # were any other parameters specified?
    kwds = {}
    units = parse_units(args.units)
    if units is not None: kwds['units'] = units
    conditions = [parse_condition(c) for c in args.conditions]
    if conditions != [] : kwds['conditions'] = conditions
    dataType = parse_data_type(args.datatype)
    if dataType is not None: kwds['data_type'] = dataType
    contacts = [parse_contact(c) for c in args.contacts]
    if contacts != [] : kwds['contacts'] = contacts
    tags = [parse_tag(t) for t in args.tags]
    if tags != []: kwds['tags'] = tags
    # This is longer than it should be, and could use some refactoring.
    # But the logic is this:
    # 1. If only one argument was given, we are getting or setting a property
    #    PROPERTY --> getting, PROPERTY=VALUE --> setting
    # 2. If two arguments were given, we are getting a property from a file.
    if nargs == 1:
        kv = args.arglist[0]
        # are we getting/setting a property from the command line?
        kv = kv.strip()
        # are we setting or getting?
        try:
            # setting: NAME=VALUE
            k,v = kv.split('=')
        except ValueError:
            # getting: NAME
            k,v = kv, None
        if v is not None:
            # setting a property
            # does the property exist?
            prop = get_property(proplist, k, case_sensitive=False)
            vtype,v = infer_value(v) # scalar, vector, matrix
            # construct the arguments to Property...
            # ... name
            kwds['name'] = k
            # ... scalars, vectors, or matrices, as appropriate
            kwds[vtype] = v
            # add the property to pifdata
            newprop = Property(**kwds)
            property_adder(proplist, prop_exists=(prop is not None))(newprop)
            return '{}'.format(pif.dumps(pifdata))
        else:
            prop = get_property(proplist, k, case_sensitive=False)
            return pif.dumps(prop)
    elif nargs == 2:
        # reading a property from a json-formatted source file
        ifile, propname = args.arglist
        # get desired property from input file
        dst = get_property(proplist, propname, case_sensitive=False)
        # parse the properties present in the source file
        props = parse_json(ifile)
        src = get_property(props, propname, case_sensitive=False)
        for k,v in iter(kwds.items()):
            setattr(src, k, v)
        if src is None:
            msg = '{} was not found in {}.'.format(propname, ifile)
            raise ValueError(msg)
        # create a function to add the property
        property_adder(proplist, prop_exists=(dst is not None))(src)
        return '{}'.format(pif.dumps(pifdata))
    else:
        # should never get here if the parser custom action did its job.
        msg = "If you're seeing this, the custom parser didn't do its job."
        raise RuntimeError(msg)


# uid
def uid(pifdata):
    """
    Gets/sets the UID for the PIF-formatted data.

    Parameters
    ----------
    :pifdata, PIF: PIF-formatted data read using pif.load.

    Returns
    -------
    There are three anticipated use cases:

      # returns the UID
      pifmod -i INPUT.pif -o OUTPUT.pif uid

      # sets the UID to "jasdk-2132-asdfkasf". If UID already exists,
      # returns os._exit(0) if the UIDs match.
      pifmod -i INPUT.pif -o OUTPUT.pif uid jasdk-2132-asdfkasf

      # sets the UID to "jasdk-2132-asdfkasf", overwriting the UID
      # if it already exists. This can break things.
      pifmod -i INPUT.pif -o OUTPUT.pif uid -f jasdk-2132-asdfkasf

    For the first case, this returns the UID, if it exists, or None.
    For the second or third case, returns nothing.
    """
    try:
        # handle cases two and three
        uidval = args.arglist[0]
        if check_tag(pifdata, 'uid'):
            # exit if UID already exists and force not specified
            # check if the UIDs match
            if not args.force:
                if pifdata.uid == uidval:
                    os._exit(0)
                else:
                    os._exit(1)
        pifdata.uid = uidval
        return '{}\n'.format(pif.dumps(pifdata))
    except IndexError:
        # handle case one
        rval = getattr(pifdata, 'uid', None)
        rval = '' if rval is None else rval
        return '{}\n'.format(rval)


def main ():
    global args
    # read PIF
    if args.ifile is not None:
        with open(args.ifile) as ifs:
            pifdata = pif.load(ifs)
    else:
        pifdata = pif.load(sys.stdin)
    # perform requested action
    if args.action == 'property':
        rval = str(property(pifdata))
    elif args.action == 'uid':
        rval = str(uid(pifdata))
    elif args.action == 'sagittariidae':
        if not isinstance(pifdata, list):
            pifdata = [pifdata]
        add_link = sagittariidae.link_factory(
			projectID='nq3X4-concept-inconel718',
			host='http://sagittariidae.adapt.mines.edu')
        for p in pifdata:
            add_link(p)
        return json.dumps(pifdata)
    else:
        msg = '{} is not a recognized action.'.format(args.action)
        raise ValueError(msg)
    # write PIF
    if args.ofile is not None:
        if authorize_overwrite(args.ofile):
            with open(args.ofile, 'w') as ofs:
                ofs.write(rval)
    else:
        sys.stdout.write(rval)
#end 'def main ():'


if __name__ == '__main__':
    try:
        start_time = time.time()
        parser = argparse.ArgumentParser(
                #prog='HELLOWORLD', # default: sys.argv[0], uncomment to customize
                description=textwrap.dedent(globals()['__doc__']),
                epilog=textwrap.dedent("""\
                    EXIT STATUS

                        0 on success

                    AUTHOR

                        Branden Kappes <bkappes@mines.edu>

                    LICENSE

                        This script is in the public domain, free from copyrights
                        or restrictions.
                        """))
        # positional parameters
        # parser.add_argument('arglist',
        #     metavar='file',
        #     type=str,
        #     nargs='*', # if there are no other positional parameters
        #     #nargs=argparse.REMAINDER, # if there are
        #     help='Files to process.')
        # optional parameters
        parser.add_argument('-i',
            '--input',
            dest='ifile',
            default=None,
            help='Specify an input filename.')
        parser.add_argument('-f',
            '--force',
            default=False,
            action='store_true',
            help='Do not prompt before overwriting files, properties, etc.')
        parser.add_argument('-o',
            '--output',
            dest='ofile',
            default=None,
            help='Specify an output filename.')
        parser.add_argument('-v',
            '--verbose',
            action='count',
            default=0,
            help='Verbose output')
        parser.add_argument('--version',
            action='version',
            version='%(prog)s 0.1')
        # add subparsers
        subparsers = parser.add_subparsers(dest='action')
        # modify or return the UID
        uid_parser = subparsers.add_parser('uid',
            help='Get/set the PIF UID.')
        # uid_parser.add_argument('-f',
        #     '--force',
        #     default=False,
        #     action='store_true',
        #     help='Force set the UID. This will overwrite the current UID, ' \
        #          'and is irreversible. The resulting file will no longer ' \
        #          'associate with the original file.')
        uid_parser.add_argument('arglist',
            metavar='UID',
            type=str,
            nargs='*', # if there are no other positional parameters
            #nargs=argparse.REMAINDER, # if there are
            help='New UID. If no UID is provided, then the current UID is ' \
                 'is returned. If a UID is provided, and one already exists ' \
                 'then these two IDs are compared.')
        # property
        property_parser = subparsers.add_parser('property',
            help='Gets/sets properties in the input PIF record.')
        # property_parser.add_argument('-f',
        #     '--force',
        #     action='store_true',
        #     help='Forcibly insert this property. If another matching ' \
        #          'property exists with the same name, it will be overwritten.')
        property_parser.add_argument('--list',
            dest='list',
            default=False,
            action='store_true',
            help='Lists the keys from the pif file and from the property ' \
                 'file (if provided) and exits.')
        property_parser.add_argument('--units',
            help='Specify the units associated with the property.')
        property_parser.add_argument('--condition',
            dest='conditions',
            metavar='CONDITION',
            action='append',
            default=[],
            help='Specify a condition under which the property was ' \
                 'determined. The format of each condition is ' \
                 'NAME=VALUE[=UNITS]. Multiple conditions may be specified. ')
        property_parser.add_argument('--data-type',
            dest='datatype',
            help='Sets the type of data that makes up the property. ' \
                 'Recognized values are MACHINE_LEARNING, COMPUTATIONAL, or ' \
                 'EXPERIMENTAL.')
        property_parser.add_argument('--contact',
            dest='contacts',
            metavar='CONTACT',
            action='append',
            default=[],
            help='Person to contact, with optional email, for more ' \
                 'information about this property. Format of the argument ' \
                 'is "NAME[,EMAIL]", e.g. "Jane Smith" would not include ' \
                 'an email; "Jane Smith,jsmith@server.com" would. Multiple ' \
                 'contacts may be specified.')
        property_parser.add_argument('--tag',
            dest='tags',
            metavar='TAG',
            action='append',
            default=[],
            help='List of string tags to hold any relevant information not ' \
                 'appropriate for any other option. Multiple tags may be ' \
                 'specified.')
        # either 1 or 2 arguments are required --> custom action
        # see 'http://stackoverflow.com/questions/4194948/python-argparse-is-there-a-way-to-specify-a-range-in-nargs'
        def required_length(nmin, nmax):
            class RequiredLength(argparse.Action):
                def __call__(self, parser, args, values, option_string=None):
                    if not nmin <= len(values) <= nmax:
                        msg = 'Option "{f}" requires between {nmin} ' \
                              'and {nmax} arguments.'.format(
                                f=self.dest, nmin=nmin, nmax=nmax
                              )
                        raise argparse.ArgumentTypeError(msg)
                    setattr(args, self.dest, values)
            return RequiredLength
        property_parser.add_argument('arglist',
            metavar='PROPERTY',
            type=str,
            nargs='+', # if there are no other positional parameters
            action=required_length(1,2),
            help='Specify which property to get/set/modify. To get an ' \
                 'existing property, PROPERTY is the name of the property ' \
                 'to retrieve. To set a nonexistant property, the argument ' \
                 'would be PROPERTY=VALUE, or to overwrite a property that ' \
                 'already exists, use the force (-f) flag with entry ' \
                 'PROPERTY=VALUE. Finally, if two arguments are given, e.g. ' \
                 'property FILE PROP, then PROP is extracted from FILE and ' \
                 'added to the output. As before, a property that already ' \
                 'exists will only be overwritten if the force (-f) flag is ' \
                 'specified.')
        # sagittariidae reference
        sagittariidae_parser = subparsers.add_parser('sagittariidae',
            help='Adds sagittariidae links to the PIF record.')
        #
        args = parser.parse_args()
        # check for correct number of positional parameters
        #if len(args.filelist) < 1:
            #parser.error('missing argument')
        # timing
        if args.verbose > 0: print time.asctime()
        main()
        if args.verbose > 0: print time.asctime()
        if args.verbose:
            delta_time = time.time() - start_time
            hh = int(delta_time/3600.); delta_time -= float(hh)*3600.
            mm = int(delta_time/60.); delta_time -= float(mm)*60.
            ss = delta_time
            print 'TOTAL TIME: {0:02d}:{1:02d}:{2:06.3f}'.format(hh,mm,ss)
        sys.exit(0)
    except KeyboardInterrupt, e: # Ctrl-C
        raise e
    except SystemExit, e: # sys.exit()
        raise e
    except LocalException, e:
        if False:
            sys.stderr.write('{}\n'.format(str(e)))
        os._exit(1)
    except Exception, e:
        if False:
            print 'ERROR, UNEXPECTED EXCEPTION'
            print str(e)
            traceback.print_exc()
        os._exit(1)
#end 'if __name__ == '__main__':'
