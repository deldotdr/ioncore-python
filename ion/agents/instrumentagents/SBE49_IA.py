#!/usr/bin/env python

"""
@file ion/agents/instrumentagents/SBE49.py
@author Steve Foley
@brief CI interface for SeaBird SBE-49 CTD
"""
import logging
logging = logging.getLogger(__name__)
from twisted.internet import defer

import SBE49_constants as const
from ion.agents.instrumentagents import instrument_agent as IA
from ion.agents.instrumentagents.instrument_agent import InstrumentAgent

from ion.core.base_process import BaseProcess, ProtocolFactory, ProcessDesc


# Gotta have this AFTER the "static" variables above
from ion.agents.instrumentagents.SBE49_driver import SBE49InstrumentDriverClient

class SBE49InstrumentAgent(InstrumentAgent):
    """
    Sea-Bird 49 specific instrument driver
    Inherits basic get, set, getStatus, getCapabilities, etc. from parent
    """

    @defer.inlineCallbacks
    def plc_init(self):
        """
        Initialize instrument driver when this process is started.
        """
        InstrumentAgent.plc_init(self)

        self.instrument_id = self.spawn_args.get('instrument-id', '123')
        self.driver_args = self.spawn_args.get('driver-args', {})
        logging.info("INIT agent for instrument ID: %s" % (self.instrument_id))

        self.driver_args['instrument-id'] = self.instrument_id
        self.pd = ProcessDesc(**{'name':'SBE49Driver',
                          'module':'ion.agents.instrumentagents.SBE49_driver',
                          'class':'SBE49InstrumentDriver',
                          'spawnargs':self.driver_args})

        driver_id = yield self.spawn_child(self.pd)
        self.driver_client = SBE49InstrumentDriverClient(proc=self,
                                                         target=driver_id)

    #@defer.inlineCallbacks
    #def plc_shutdown(self):
    #    yield self.pd.shutdown()


    @staticmethod
    def __translator(input):
        """
        A function (to be returned upon request) that will translate the
        very raw data from the instrument into the common archive format
        """
        return input

    @defer.inlineCallbacks
    def op_get_translator(self, content, headers, msg):
        """
        Return the translator function that will convert the very raw format
        of the instrument into a common OOI repository-ready format
        """
        yield self.reply_err(msg, "Not Implemented!")
#        yield self.reply_ok(msg, self.__translator)

    @defer.inlineCallbacks
    def op_get_capabilities(self, content, headers, msg):
        """
        Obtain a list of capabilities that this instrument has. This is
        simply a command and parameter list at this point
        """
        yield self.reply(msg, 'get_capabilities',
                         {IA.instrument_commands: const.instrument_commands,
                          IA.instrument_parameters: const.instrument_parameters,
                          IA.ci_commands: const.ci_commands,
                          IA.ci_parameters: const.ci_parameters}, {})

# Spawn of the process using the module name
factory = ProtocolFactory(SBE49InstrumentAgent)
