#!/usr/bin/env python

"""
@file ion/core/ioninit.py
@author Michael Meisinger
@brief definitions and code that needs to run for any use of ion
"""

import logging
import logging.config
import re
import os

from ion.core import ionconst as ic
from ion.util.config import Config

#print "ION (Integrated Observatory Network) core packages initializing (ver. %s)" % (ic.VERSION)

# ION has a minimum required python version
import sys
if not hasattr(sys, "version_info") or sys.version_info < (2,5):
    raise RuntimeError("ioncore requires Python 2.5 or later.")
if sys.version_info > (3,0):
    raise RuntimeError("ioncore is not compatible with Python 3.0 or later.")
del sys

# The following code looking for a ION_ALTERNATE_LOGGING_CONF environment
# variable can go away with the new ion environment directories 

# Configure logging system (console, logfile, other loggers)
# NOTE: Console logging is appended to Twisted log output prefix!!
if os.environ.has_key(ic.ION_ALTERNATE_LOGGING_CONF):
    altpath = os.environ.get(ic.ION_ALTERNATE_LOGGING_CONF)
    logging.config.fileConfig(altpath)
else:
    logging.config.fileConfig(ic.LOGCONF_FILENAME)
    
# Load configuration properties for any module to access
ion_config = Config(ic.ION_CONF_FILENAME)

# Update configuration with local override config
ion_config.update_from_file(ic.ION_LOCAL_CONF_FILENAME)

# Arguments given to the container (i.e. the python process executing this code)
cont_args = {}

# Always refers to current container singleton instance, once first initialized
container_instance = None

# The name shared by all containers of one system (i.e. cluster name)
sys_name = None

# Global flag determining whether currently running unit test
testing = True

def config(name):
    """
    Get a subtree of the global configuration, typically for a module
    """
    return Config(name, ion_config)

def get_config(confname, conf=None):
    """
    Returns a Config instance referenced by the file name in the system config's
    entry
    @param confname  entry in the conf configuration
    @param conf None for system config or different config
    """
    if conf == None:
        conf = ion_config
    return Config(conf.getValue(confname)).getObject()

def adjust_dir(filename):
    """
    @brief Compensates for different current directories in tests and production
    """
    if not filename:
        return None
    #if testing:
    if os.getcwd().endswith("_trial_temp"):
        return "../" + filename
    else:
        return filename

def install_msgpacker():
    from carrot.serialization import registry
    import msgpack
    registry.register('msgpack', msgpack.packb, msgpack.unpackb, content_type='application/msgpack', content_encoding='binary')
    registry._set_default_serializer('msgpack')

install_msgpacker()

def set_log_levels(levelfilekey=None):
    """
    Sets logging levels of per module loggers to given values. Loggers of
    packages are higher in the chain of module specific loggers.
    If called with None argument, will read the global and local files with
    log levels. Otherwise, read the file indicated by filename and if it exists,
    set the log levels as given.
    """
    if levelfilekey == None:
        set_log_levels('loglevels')
        set_log_levels('loglevelslocal')
    else:
        levellistkey = ion_config.getValue2(__name__, levelfilekey, None)
        levellist = None
        try:
            filecontent = open(levellistkey,).read()
            # Eval file content in the namespace of the logging module, such
            # that constants like DEBUG are resolved correctly
            levellist = eval(filecontent, logging.__dict__)
        except IOError, ioe:
            pass
        except Exception, ex:
            print ex
        if not levellist:
            return
        assert type(levellist) is list
        for level in levellist:
            logging.getLogger(level[0]).setLevel(level[1])

set_log_levels()

#def augment_logging():
#    """
#    HACK: Replace the getLogger function in the logging module, such that it
#    adds a Log
#    """
#    from ion.util import ionlogging
#    getlogger = logging.getLogger
#    def ion_getLogger(loggername, *args, **kwargs):
#        logger = getlogger(loggername, *args, **kwargs)
#        ladapter = ionlogging.LoggerAdapter(logger, ionlogging.ProcessInfo())
#        return ladapter
#    logging.getLogger = ion_getLogger
#
#augment_logging()

# HACKHACK: Putz with Twisted's twisted.python.log facility
# The goal is to get rid of the prefix in each line before the message
def clean_twisted_logging():
    from twisted.python import log, util
    obs0 = log.theLogPublisher.observers[0]
    ro = log.removeObserver
    if not hasattr(obs0.im_self,'write'):
        # In case of trial testcases this hack does not work.
        return
    fdwrite = obs0.im_self.write
    fdflush = obs0.im_self.flush
    def log_emit(eventDict):
        text = log.textFromEventDict(eventDict)
        if text is None:
            return
        util.untilConcludes(fdwrite, text + "\n")
        util.untilConcludes(fdflush)
    def remove_nop(obs):
        if obs != obs0:
            ro(obs)
    log.theLogPublisher.removeObserver(obs0)
    log.theLogPublisher.addObserver(log_emit)
    log.removeObserver = remove_nop

clean_twisted_logging()
