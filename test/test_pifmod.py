import sys, os
import subprocess as sub
import shlex
import json
from pypif import pif
import difflib

# To test, simply run
# [...]$ nosetests (optionally with -v)
# and a report a summary of the results

# test the expected use cases...
def execute(command, **kwds):
	args = shlex.split(command)
	kwds['stdout'] = kwds.get('stdout', sub.PIPE)
	kwds['stderr'] = kwds.get('stderr', sub.PIPE)
	if kwds.has_key('stdin'):
		kwds['stdin'] = open(kwds['stdin'])
	p = sub.Popen(args, **kwds)
	if kwds.has_key('stdin'):
		kwds['stdin'].close()
	out, err = p.communicate()
	return (p.returncode, out.strip(), err.strip())

def empty(line):
	return line == ''

def compare_dictionaries(a, b):
	def equals(lhs, rhs):
		if isinstance(lhs, dict) and isinstance(rhs, dict):
			return compare_dictionaries(lhs, rhs)
		elif isinstance(lhs, list) and isinstance(rhs, list):
			return all([equals(l, r) for l,r in zip(lhs, rhs)])
		else:
			return lhs == rhs
	keys_match = all([ka == kb for ka, kb in
		zip(sorted(a.keys()), sorted(b.keys()))])
	values_match = all([equals(a[k], b[k]) for k in a.keys()])
	return keys_match and values_match

def strdiff(a, b):
	remove = lambda i,s: u'Delete "{}" from position {}'.format(s, i)
	insert = lambda i,s: u'Insert "{}" at position {}'.format(s, i)
	result = []
	for i,s in enumerate(difflib.ndiff(a, b)):
		if s[0] == '':
			continue
		elif s[0] == '-':
			result.append(remove(i, s[1]))
		elif s[0] == '+':
			result.append(insert(i, s[1]))
	return result

class TestClass: # keep this the same
	def setUp(self):
		# construct objects and perform any necessary setup
		self.pif_uid = 'fc836afc-773e-de46-f808-568265077c05'

	def test_return_uid_Ifile(self):
		rval, out, err = execute('pifmod -i data/pif.json uid')
		assert rval == 0, 'Nonzero ({}) exit status.'.format(rval)
		assert out == self.pif_uid, \
			'UIDs do not match ({} != {})'.format(out, self.pif_uid)
		assert empty(err)

	def test_return_uid_stdin(self):
		rval, out, err = execute('pifmod uid', stdin='data/pif.json')
		assert rval == 0, 'Nonzero ({}) exit status.'.format(rval)
		assert out == self.pif_uid, \
			'UIDs do not match ({} != {})'.format(out, self.pif_uid)
		assert empty(err)

	def test_check_uid_Ifile_good(self):
		rval, out, err = execute(
			'pifmod -i data/pif.json uid {}'.format(self.pif_uid))
		assert rval == 0, 'Nonzero ({}) exit status.'.format(rval)
		assert empty(out)
		assert empty(err)

	def test_check_uid_Ifile_bad(self):
		rval, out, err = execute(
			'pifmod -i data/pif.json uid 12345678987654321')
		assert rval != 0, 'Nonzero ({}) exit status expected.'.format(rval)
		assert empty(out)
		assert empty(err)

	def test_property_listing_Ifile(self):
		rval, out, err = execute('pifmod -i data/pif.json ' \
			'property --list data/pore-distribution.json')
		expected = '\n'.join(['PIF data',
							  '- median pore spacing',
							  'data/pore-distribution.json',
							  '- Pore ID',
							  '- center of mass Z',
							  '- center of mass X',
							  '- center of mass Y',
							  '- median pore spacing',
							  '- nearest neighbor distance',
							  '- volume'])
		assert out == expected, '+{}+ != \n+{}+'.format(out, expected)
		assert empty(err)

	def test_property_return_property_Ifile(self):
		rval, out, err = execute('pifmod -i data/pif.json ' \
			'property "median pore spacing"')
		expected = {"scalars": 50.40827706835452,
				    "units": "$\\mu$m",
				    "name": "median pore spacing"}
		expected = json.dumps(expected)
		received = json.loads(out)
		assert out == expected, \
			'{} !=\n{}'.format(expected, received)

	def test_property_return_property_stdin(self):
		rval, out, err = execute('pifmod property "median pore spacing"',
								 stdin='data/pif.json')
		expected = {"scalars": 50.40827706835452,
				    "units": "$\\mu$m",
				    "name": "median pore spacing"}
		expected = json.dumps(expected)
		received = json.loads(out)
		assert out == expected, \
			'{} !=\n{}'.format(expected, received)

	def test_property_add_Ifile(self):
		rval, out, err = execute('pifmod -i data/pif.json -o data/test.pif ' \
			'property foo=bar')
		with open('data/out.pif') as ifs:
			expected = pif.load(ifs)
		with open('data/test.pif') as ifs:
			received = pif.load(ifs)
		assert rval == 0
		assert empty(out)
		assert empty(err)
		assert compare_dictionaries(expected.as_dictionary(),
									received.as_dictionary()), \
			'\n'.join(strdiff(pif.dumps(expected), pif.dumps(received)))

	def test_property_add_units_Ifile(self):
		# with units...
		rval, out, err = execute('pifmod -i data/pif.json -o data/test.pif ' \
			'property --units=mm foo=bar')
		with open('data/out_units.pif') as ifs:
			expected = pif.load(ifs)
		with open('data/test.pif') as ifs:
			received = pif.load(ifs)
		assert rval == 0
		assert empty(out)
		assert empty(err)
		assert compare_dictionaries(expected.as_dictionary(),
									received.as_dictionary()), \
			'\n'.join(strdiff(pif.dumps(expected), pif.dumps(received)))

	def test_property_add_conditions_Ifile(self):
		# with conditions...
		rval, out, err = execute('pifmod -i data/pif.json -o data/test.pif ' \
			'property --condition="laser=95=%" --condition="gas=Ar" ' \
			'foo=bar')
		with open('data/out_conditions.pif') as ifs:
			expected = pif.load(ifs)
		with open('data/test.pif') as ifs:
			received = pif.load(ifs)
		assert rval == 0
		assert empty(out)
		assert empty(err)
		assert compare_dictionaries(expected.as_dictionary(),
									received.as_dictionary()), \
			'\n'.join(strdiff(pif.dumps(expected), pif.dumps(received)))

	def test_property_add_datatype_Ifile(self):
		# with data type...
		rval, out, err = execute('pifmod -i data/pif.json -o data/test.pif ' \
			'property --data-type=EXPERIMENTAL foo=bar')
		with open('data/out_datatype.pif') as ifs:
			expected = pif.load(ifs)
		with open('data/test.pif') as ifs:
			received = pif.load(ifs)
		assert rval == 0
		assert empty(out)
		assert empty(err)
		assert compare_dictionaries(expected.as_dictionary(),
									received.as_dictionary()), \
			'\n'.join(strdiff(pif.dumps(expected), pif.dumps(received)))

	def test_property_add_contacts_Ifile(self):
		# with contacts...
		rval, out, err = execute('pifmod -i data/pif.json -o data/test.pif ' \
			'property --contact="Branden Kappes,bkappes@mines.edu" ' \
			'foo=bar')
		with open('data/out_contact.pif') as ifs:
			expected = pif.load(ifs)
		with open('data/test.pif') as ifs:
			received = pif.load(ifs)
		assert rval == 0
		assert empty(out)
		assert empty(err)
		assert compare_dictionaries(expected.as_dictionary(),
									received.as_dictionary()), \
			'{}'.format(strdiff(pif.dumps(expected), pif.dumps(received)))

	def test_property_add_tags_Ifile(self):
		# with tags...
		rval, out, err = execute('pifmod -i data/pif.json -o data/test.pif ' \
			'property --tag="Hello World" foo=bar')
		with open('data/out_tags.pif') as ifs:
			expected = pif.load(ifs)
		with open('data/test.pif') as ifs:
			received = pif.load(ifs)
		assert rval == 0
		assert empty(out)
		assert empty(err)
		assert compare_dictionaries(expected.as_dictionary(),
									received.as_dictionary()), \
			'{}'.format(strdiff(pif.dumps(expected), pif.dumps(received)))

	def test_property_add_volume_Ifile(self):
		# with tags...
		rval, out, err = execute('pifmod -i data/pif.json -o data/test.pif ' \
			'property data/pore-distribution.json volume')
		with open('data/out_volume.pif') as ifs:
			expected = pif.load(ifs)
		with open('data/test.pif') as ifs:
			received = pif.load(ifs)
		assert rval == 0
		assert empty(out)
		assert empty(err)
		assert compare_dictionaries(expected.as_dictionary(),
									received.as_dictionary()), \
			'{}'.format(strdiff(pif.dumps(expected), pif.dumps(received)))

	def tearDown(self):
		# clean up
		if os.path.isfile('data/test.pif'):
			os.remove('data/test.pif')
