import sys
sys.path.append('..')
from NAME.MODULE import METHOD

# To test, simply run
# [...]$ nosetests (optionally with -v)
# and a report a summary of the results

class TestClass: # keep this the same
	def setUp(self):
		# construct objects and perform any necessary setup
		pass

	def test_UNIT_1(self):
		# run test one
		assert 1 == 1 # assertion, if false, fails
		pass

	def test_UNIT_2(self):
		# run test two
		assert 2 == 2 # assertion, if false, fails
		pass

	# ...

	def tearDown(self):
		# clean up
		pass

