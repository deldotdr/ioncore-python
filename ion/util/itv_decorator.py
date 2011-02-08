#!/usr/bin/env python

"""
@file ion/util/itv_decorator.py
@author David Stuebe
@todo Make the skip specific to a class within a test module?
@brief Unit test decorator that skips unit/integration tests based on the
ion configuration file. This lets us separate integration tests for buildbot.
@note Experimental code!

To use this, add an entry to res/config/ion.config, keyed to the name
of your file. Here's the config for the unit tests:


'ion.util.test._trial_decorator': {
    'test_that_skips' : False,
    'test_that_passes' : True,
    'test_skiptest' : True,
},

In this case, test_that_skips is not run - anything marked False
is skipped.
"""

from twisted.trial import unittest
from ion.core import ioninit
CONF = ioninit.config(__name__)

class itv(object):

    def __init__(self, config):
        self.config = config

    def __call__(self, func):

        # Get the config for a particular test - the developer can
        # choose to run a particular test using this
        run_test = self.config.getValue(func.__name__, False)

        # This is a global override to run all ITV
        if CONF.getValue('Run ITV Tests', False):
           run_test = True


        if run_test:
            my_func = func
            
        else:
            def my_func(*args, **kwargs):
                strng = 'Skipping the %s integration test.' % func.__name__
                raise unittest.SkipTest(strng)
                
        return my_func

