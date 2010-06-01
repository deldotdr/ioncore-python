#!/usr/bin/env python
"""
@file ion/services/dm/proxy.py
@author Paul Hubbard
@date 5/25/10
@package ion.services.dm.proxy http->ooi proxy for user DAP access
Porting from LCO implementation to new LCA arch - complete rewrite.
"""

import logging

from twisted.internet import defer, reactor
from twisted.web import proxy
from twisted.web.http import Request, HTTPFactory
from magnet.spawnable import Receiver
from ion.core.base_process import ProtocolFactory


from ion.services.base_service import BaseService
from ion.services.dm.coordinator import CoordinatorClient

class ProxyRequest(Request):
    """
    Used by Proxy to implement a simple web proxy.
    We override process() method to send a dap_get request to the controller
    which forwards it to the fetcher.

    @see http://twistedmatrix.com/documents/current/api/twisted.web.proxy.ProxyRequest.html
    """
    @defer.inlineCallbacks
    def process(self):
        logging.debug('Processing request to %s' % self.uri)
        cc = CoordinatorClient()
        msg = yield cc.get_url(self.uri)
        logging.debug('Returning %d bytes of data' % len(msg))
        defer.returnValue(msg)

class ProxyService(BaseService):
    """
    Proxy service. Stub, really, since the proxy listens on a plain tcp port.
    """
    # Declaration of service
    declare = BaseService.service_declare(name='proxy',
                                          version='0.1.0',
                                          dependencies=['controller'])

    def __init__(self, receiver, spawnArgs=None):
        # @todo save father!
        # Service class initializer. Basic config, but no yields allowed.
        BaseService.__init__(self, receiver, spawnArgs)
        logging.info('ProxyService.__init__()')

    def slc_init(self):
        """
        Use this hook to bind to listener TCP port and setup modified
        proxy stack.
        """
        # @todo Move tcp port to DX configuration file

        tcp_port = 10001
        logging.debug('Setting up TCP listener on port %d...' % tcp_port)
        hf = HTTPFactory()
        proxy.Proxy.requestFactory = ProxyRequest
        hf.protocol = proxy.Proxy
        reactor.listenTCP(tcp_port, hf)
        logging.debug('Proxy listener running.')

factory = ProtocolFactory(ProxyService)