#!/usr/bin/env python

"""
@file ion/data/datastore/test/test_rdfstore.py
@author David Stuebe
@author Dorian Raymer
@brief test rdf store
"""

import logging

from twisted.internet import defer
from twisted.trial import unittest

from ion.data import store
from ion.data import set_store
from ion.data.datastore import cas
from ion.data.datastore import objstore
from ion.data.datastore import rdfstore
from ion.data import resource

sha1 = cas.sha1

class AssociationBaseTest(unittest.TestCase):

    def setUp(self):
        self.subject = cas.Blob('ASubject')
        self.predicate = cas.Blob('APredicate')
        self.object = cas.Blob('AObject')
        self.association = rdfstore.Association(self.subject,self.predicate,self.object)
        #print self.association
        #print objstore.Blob(self.subject)

    def test_type(self):
        self.failUnlessEqual(self.association.type, 'association')
        
    def test_match(self):
        self.assert_(self.association.match(self.subject))
        self.assertNot(self.association.match(cas.Blob('NO Match')))
        self.assertNot(self.association.match(cas.Blob('No Match'),position=rdfstore.OBJECT))
        self.assert_(self.association.match(self.subject,position=rdfstore.SUBJECT))
        self.assert_(self.association.match(self.predicate,position=rdfstore.PREDICATE))
        self.assertNot(self.association.match(self.subject,position=rdfstore.PREDICATE))      
        self.assertRaises(KeyError,self.association.match,self.subject,position='blahblahblah')

    @defer.inlineCallbacks
    def test_put_get(self):
        s = yield store.Store.create_store()
        castore = cas.CAStore(s)
        logging.info(str(self.association))

        castore.TYPES[rdfstore.Association.type]=rdfstore.Association
        
        a_id = yield castore.put(self.association)
        
        assoc = yield castore.get(a_id)
        
        logging.info(str(assoc))
        
        self.assertEqual(self.association.value,assoc.value)
        


        
#class RdfStoreTest(unittest.TestCase):
#    """
#    """
#    @defer.inlineCallbacks
#    def setUp(self):
#        s = yield store.Store.create_store()
#        ss = yield set_store.SetStore.create_store()
#        self.mystore = yield rdfstore.RdfStore.new(s, ss, 'test_partition')
#        
#    @defer.inlineCallbacks
#    def test_create_object(self):
#        rdfchassis = yield self.mystore.create('thing', resource.IdentityResource)
#        self.assert_(isinstance(rdfchassis, rdfstore.RdfChassis))
#
#        id_res = yield rdfchassis.checkout()
#        self.assert_(isinstance(id_res, resource.IdentityResource))
#        id_res.name = 'Carlos S'
#        id_res.email = 'carlos@ooici.biz'
#        
#        rdfchassis.commit()
#        
#    @defer.inlineCallbacks
#    def test_checkout_object(self):
#        rdfchassis = yield self.mystore.create('thing', resource.IdentityResource)
#        id_res = yield rdfchassis.checkout()
#        id_res.name = 'Carlos S'
#        id_res.email = 'carlos@ooici.biz'
#        rdfchassis.commit()
#        id_res = yield rdfchassis.checkout()
      
        
        
        
        
        