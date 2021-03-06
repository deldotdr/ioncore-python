#!/usr/bin/env python

"""
@file res/scripts/bootstrap-dx.py
@author Paul Hubbard
@brief main module for bootstrapping data exchange
"""

import logging
from twisted.internet import defer

from ion.core import ioninit
from ion.core import bootstrap

CONF = ioninit.config('startup.bootstrap-dx')

# Static definition of message queues
ion_messaging = ioninit.get_config('messaging_cfg', CONF)

# Static definition of service names
dx_services = ioninit.get_config('services_cfg', CONF)


@defer.inlineCallbacks
def start():
    """
    Main function of bootstrap. Starts DX system with static config
    """
    logging.info("ION/DX bootstrapping now...")
    startsvcs = []
    startsvcs.extend(dx_services)

    yield bootstrap.bootstrap(ion_messaging, startsvcs)

start()
