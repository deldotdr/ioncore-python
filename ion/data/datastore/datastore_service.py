#!/usr/bin/env python

"""
@file ion/play/rdf_store/rdf_service.py
@package ion.play.rdf_store.rdf_service
@author David Stuebe
@brief A service that provides git symantics for push pull commit and diff to
the rdf workspace composed of associations and objects.
The associations can be walked to find content.
"""

import logging
logging = logging.getLogger(__name__)
from twisted.internet import defer
from magnet.spawnable import Receiver

import ion.util.procutils as pu
from ion.core.base_process import ProtocolFactory
from ion.services.base_service import BaseService, BaseServiceClient

class DataStoreService(BaseService):
    """
    Example service interface
    """
    # Declaration of service
    declare = BaseService.service_declare(name='DataStoreService',
                                          version='0.1.0',
                                          dependencies=[])

    def __init__(self, receiver, spawnArgs=None):
        """
        @brief Init method for the DataStore Frontend service
        @param frontend - an instance of a CAStore Frontend
        """
        # Service class initializer. Basic config, but no yields allowed.
        self.frontend = spawnArgs['MyFrontend']
        BaseService.__init__(self, receiver, spawnArgs)
        logging.info('DataStoreService.__init__()')

#    @defer.inlineCallbacks
    def slc_init(self):
        pass

    @defer.inlineCallbacks
    def op_push(self, content, headers, msg):
        logging.info('op_push: '+str(content)+ ', Remote Frontend:'+self.frontend)



        # The following line shows how to reply to a message
        yield self.reply_ok(msg)

    @defer.inlineCallbacks
    def op_pull(self, content, headers, msg):
        logging.info('op_pull: '+str(content) + ', Remote Frontend:'+self.frontend)


        # The following line shows how to reply to a message
        yield self.reply_ok(msg)

    @defer.inlineCallbacks
    def op_clone(self, content, headers, msg):
        logging.info('op_clone: '+str(content)+ ', Remote Frontend:'+self.frontend)

        # The following line shows how to reply to a message
        yield self.reply_ok(msg)



class DataStoreServiceClient(BaseServiceClient):
    """
    This is an exemplar service client that calls the hello service. It
    makes service calls RPC style.
    """
    def __init__(self, frontend, proc=None, **kwargs):
        """
        @brief Init method for the DataStore Frontend client
        @param frontend - an instance of a CAStore Frontend
        """
        if not 'targetname' in kwargs:
            kwargs['targetname'] = "DataStoreService"
        BaseServiceClient.__init__(self, proc, **kwargs)
        self.frontend=frontend
        logging.info('DataStoreServiceClient.__init__()')


#    @defer.inlineCallbacks
    def slc_init(self):
#        yield self.rdfs.init()
        pass

    @defer.inlineCallbacks
    def push(self, repository_name,permit_bracnch=False):
        """
        @brief Push the content of a local repository to the service data store
        @param repository_name - the name (key) of a repository in the local datastore
        """
        yield self._check_init()
        logging.info('pushing: '+repository_name+ ', Local Frontend:'+self.frontend)
        (content, headers, msg) = yield self.rpc_send('push', repository_name)

        """
        Steps:
        Send the commit DAG to the service
        Receive the Commits which need to be pushed
        Send the commit trees
        Receive OK
        """

        logging.info('Service reply: '+str(content))
        defer.returnValue(str(content))

    @defer.inlineCallbacks
    def pull(self, repository_name):
        """
        @brief Pull the latest changes from the remote datastore
        @param repository_name - the name (key) of a repository in the remote datastore
        """
        yield self._check_init()
        logging.info('pulling: '+repository_name+ ', Local Frontend:'+self.frontend)
        """
        Steps:
        Send the current commit DAG to the service
        Receive the Commits which need to be pulled
        """

        (content, headers, msg) = yield self.rpc_send('pull', repository_name)
        logging.info('Service reply: '+str(content))
        defer.returnValue(str(content))


    @defer.inlineCallbacks
    def clone(self, repository_name):
        """
        @brief Clone a repository to the local object store from the remote datastore
        @param repository_name - the name (key) of a repository in the remote datastore
        """
        yield self._check_init()
        logging.info('cloning: '+repository_name+ ', Local Frontend:'+self.frontend)
        """
        Steps:
        Send the repo name
        Receive the Commits which need to be pulled
        """
        (content, headers, msg) = yield self.rpc_send('clone', repository_name)
        logging.info('Service reply: '+str(content))
        defer.returnValue(str(content))




# Spawn of the process using the module name
factory = ProtocolFactory(DataStoreService)
