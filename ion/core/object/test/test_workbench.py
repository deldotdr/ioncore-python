#!/usr/bin/env python
"""
@Brief Test implementation of the workbench class

@file ion/core/object
@author David Stuebe
@test The object managment WorkBench class
"""

import ion.util.ionlog
log = ion.util.ionlog.getLogger(__name__)
from uuid import uuid4

from twisted.trial import unittest
#from twisted.internet import defer

from ion.test.iontest import IonTestCase

from net.ooici.play import addressbook_pb2

from ion.core.object import gpb_wrapper
from ion.core.object import repository
from ion.core.object import workbench


class WorkBenchTest(unittest.TestCase):
        
    def setUp(self):
        wb = workbench.WorkBench('No Process Test')
        self.wb = wb
        
        repo, ab = self.wb.init_repository(addressbook_pb2.AddressLink)

                        
        p = repo.create_wrapped_object(addressbook_pb2.Person)
        p.name='David'
        p.id = 5
        p.email = 'd@s.com'
        ph = p.phone.add()
        ph.type = p.WORK
        ph.number = '123 456 7890'
        
        ab.owner = p
            
        ab.person.add()
        ab.person[0] = p
        
        ab.person.add()
        p = repo.create_wrapped_object(addressbook_pb2.Person)
        p.name='John'
        p.id = 78
        p.email = 'J@s.com'
        ph = p.phone.add()
        ph.type = p.WORK
        ph.number = '111 222 3333'
        
        ab.person[1] = p
        
        self.ab = ab
        self.repo = repo
        
        
            
    def test_simple_commit(self):
        
        cref = self.repo.commit(comment='testing commit')
        print 'Commited',cref
        
        
    def test_pack_root(self):
        
        serialized = self.wb.pack_structure(self.ab)
        
        print serialized
            
    
    def test_pack_mutable(self):
        serialized = self.wb.pack_structure(self.repo._dotgit)
        
        
    def test_pack_root_eq_unpack(self):
        
        serialized = self.wb.pack_structure(self.ab)
            
        res = self.wb.unpack_structure(serialized)
        
        self.assertEqual(res,self.ab)
        
        
    def test_pack_mutable_eq_unpack(self):
            
        serialized = self.wb.pack_structure(self.repo._dotgit)
            
        repo = self.wb.unpack_structure(serialized)
        
        self.assertEqual(repo._dotgit, self.repo._dotgit)
        
        ab=repo.checkout(branch_name='master')
        
        self.assertEqual(ab, self.ab)
            
            
        
    def test_pack_repository_commits(self):
        
        self.repo.commit('testing repository packing')
        
        serialized = self.wb.pack_repository_commits(self.repo)
        
        repo = self.wb.unpack_structure(serialized)
        
        self.assertEqual(repo._dotgit, self.repo._dotgit)
        
        commit = repo._dotgit.branches[0].commitref
        
        
        #Check that the commit came through
        self.assertEqual(commit, self.repo._current_branch.commitref)
        
        
        
        
        
        