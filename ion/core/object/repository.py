#!/usr/bin/env python


"""
@Brief Repository for managing data structures
@author David Stuebe
@author Matt Rodriguez

TODO
Create exception class and move stuff to a object utils module
Make sure delete works for these objects the way we expect!

"""

import ion.util.ionlog
log = ion.util.ionlog.getLogger(__name__)

import sys

from net.ooici.core.mutable import mutable_pb2

from twisted.internet import defer

from ion.core.object import gpb_wrapper

from ion.util import procutils as pu

from net.ooici.core.type import type_pb2
from net.ooici.core.link import link_pb2


class Repository(object):
    
    UPTODATE='up to date'
    MODIFIED='modified'
    NOTINITIALIZED = 'This repository is not initialized yet'

    CommitClassType = gpb_wrapper.set_type_from_obj(mutable_pb2.CommitRef())
    LinkClassType = gpb_wrapper.set_type_from_obj(link_pb2.CASRef())
    
    def __init__(self, head=None):
        
        
        #self.status  is a property determined by the workspace root object status
        
        self._object_counter=1
        """
        A counter object used by this class to identify content objects untill
        they are indexed
        """
        
        self._workspace = {}
        """
        A dictionary containing objects which are not yet indexed, linked by a
        counter refrence in the current workspace
        """
        
        self._workspace_root = None
        """
        Pointer to the current root object in the workspace
        """
        
        self._commit_index = {}
        """
        A dictionary containing the commit objects - all immutable content hashed
        """
        
        self._hashed_elements = None
        """
        All content elements are stored here - from incoming messages and
        new commits - everything goes here. Now it can be decoded for a checkout
        or sent in a message.
        """
        
        
        self._current_branch = None
        """
        The current branch object of the mutable head
        Branch names are generallly nonsense (uuid or some such)
        """
        
        self.branchnicknames = {}
        """
        Nick names for the branches of this repository - these are purely local!
        """
        
        self._detached_head = False
        
        
        self._merged_from = []
        """
        Keep track of branches which were merged into this one!
        Like _current_brach, _merged_from is a list of links - not the actual
        commit refs
        """
        
        self._stash = {}
        """
        A place to stash the work space under a saved name.
        """
        
        self._workbench=None
        """
        The work bench which this repository belongs to...
        """

        if head:
            self._dotgit = self._load_element(head)
        else:
           
            self._dotgit = self.create_wrapped_object(mutable_pb2.MutableNode, addtoworkspace = False)
            self._dotgit.repositorykey = pu.create_guid()
        """
        A specially wrapped Mutable GPBObject which tracks branches and commits
        It is not 'stored' in the index - it lives in the workspace
        """
    
    @property
    def repository_key(self):
        return self._dotgit.repositorykey
    
    @property
    def branches(self):
        return self._dotgit.branches
        
    def get_branch(self,name):
        branchkey = self.branchnicknames.get(name,None)
        if not branchkey:
            branchkey = name
        
        branch = None
        for item in self.branches:
            if item.branchkey == branchkey:
                branch = item
                break
        else:
            log.info('Branch %s not found!' % name)
            
        return branch
            
        
        
        
        
    def checkout(self, branchname=None, commit_id=None, older_than=None):
        """
        Check out a particular branch
        Specify a branch, a branch and commit_id or a date
        Branch can be either a local nick name or a global branch key
        """
        
        if self.status == self.MODIFIED:
            raise Exception, 'Can not checkout while the workspace is dirty'
            #What to do for uninitialized? 
        
        #Declare that it is a detached head!
        detached = False
        
        if older_than and commit_id:
            raise Exception, 'Checkout called with both commit_id and older_than!'
        
        if not branchname:
            raise Exception, 'Checkout must specify a branchname!'
            
            
        branch = self.get_branch(branchname)
        if not branch:
            raise Exception, 'Branch Key: "%s" does not exist!' % branchkey
            
        if len(branch.commitrefs)==0:
            raise Exception, 'This branch is empty - there is nothing to checkout!'
            
        
        # Set the current branch now!
        self._current_branch = branch
        
        cref = None
            
        if commit_id:
            
            # IF you are checking out a specific commit ID it is always a detached head!
            detached = True
            
            # Use this set to make sure we only examine each commit once!
            touched_refs = set()
                
            crefs = branch.commitrefs[:]
            
            while len(crefs) >0:
                new_set = set()
                    
                for ref in crefs:
                        
                    if ref.myid == commit_id:
                        
                        # Empty the crefs set to exit the while loop!
                        crefs = set()
                        # Save the CRef!
                        cref = ref
                        break # Break to ref in crefs
                        
                    # For each child reference...
                    for pref in ref.parentrefs:
                        # If we have not already looked at this one...
                        p_commit = pref.commitref
                        if not p_commit in touched_refs:                            
                            new_set.add(p_commit)
                            touched_refs.add(p_commit)    
                    
                else:
                    crefs = new_set                    
            else:
                if not cref:
                    raise Exception, 'End of Ancestors: No matching reference found in commit history on branch name %s, commit_id: %s' % (branch_name, commit_id)
                
            
            
        elif older_than:
            
            # IF you are checking out a specific commit date it is always a detached head!
            detached = True
            
            # Need to make sure we get the closest commit to the older_than date!
            younger_than = -9999.99
            
            # Use this set to make sure we only examine each commit once!
            touched_refs = set()
            
            crefs = branch.commitrefs[:]
            
            while len(crefs) >0:
                
                new_set = set()
                
                for ref in crefs:
                        
                    if ref.date <= older_than & ref.date > younger_than:
                        cref = ref
                        younger_than = ref.date
                        
                    # Only keep looking at parent references if they are to young
                    elif ref.date > older_than:
                        # For each child reference...
                        for pref in ref.parentrefs:
                            # If we have not already looked at this one...
                            if not pref in touched_refs:                            
                                new_set.add(pref)
                                touched_refs.add(pref)    
                       
                crefs = new_set
                       
            else:
                if not cref:
                    raise Exception, 'End of Ancestors: No matching commit found in commit history on branch name %s, older_than: %s' % (branch_name, older_than)
                
        # Just checking out the current head - need to make sure it has not diverged! 
        else:
            
            if len(branch.commitrefs) ==1:
                
                cref = branch.commitrefs[0]
                
            else:
                log.warn('BRANCH STATE HAS DIVERGED - MERGING') 
                
                cref = self.merge_by_date(branch)
                
                
        
        # Do some clean up!
        self._workspace = {}
        self._workspace_root = None
            
            
        # Automatically fetch the object from the hashed dictionary or fetch if needed!
        rootobj = cref.objectroot
        self._workspace_root = rootobj
        
        self._load_links(rootobj)
        
        
        self._detached_head = detached
        
        if detached:
            self._current_branch = self.create_wrapped_object(mutable_pb2.Branch, addtoworkspace=False)
            bref = self._current_branch.commitrefs.add()
            bref.set_link(cref)
            self._current_branch.branchkey = 'detached head'
            
            rootobj._set_structure_read_only()
            
            
        return rootobj
        
        
    def merge_by_date(self, branch):
        
        crefs=branch.commitrefs[:]
        
        newest = -999.99
        for cref in crefs:
            if cref.date > newest:
                head_cref = cref
                newest = cref.date
            
        # Deal with the newest ref seperately
        crefs.remove(head_cref)
            
        cref = self.create_wrapped_object(mutable_pb2.CommitRef, addtoworkspace=False)
                    
        cref.date = pu.currenttime()

        pref = cref.parentrefs.add()
        pref.set_link_by_name('commitref',head_cref)
        pref.relationship = pref.Parent

        cref.set_link_by_name('objectroot', head_cref.objectroot)

        cref.comment = 'Merged divergent branch by date keeping the newest value'

        for ref in crefs:
            pref = cref.parentrefs.add()
            pref.set_link_by_name('commitref',ref)
            pref.relationship = pref.MergedFrom
        
        structure={}                            
        # Add the CRef to the hashed elements
        cref._recurse_commit(structure)
        
        # set the cref to be readonly
        cref.readonly = True
        
        # Add the cref to the active commit objects - for convienance
        self._commit_index[cref.myid] = cref

        # update the hashed elements
        self._hashed_elements.update(structure)
        
        del branch.commitrefs[:]
        bref = branch.commitrefs.add()
        bref.set_link(cref)
        
        return cref
        
    def reset(self):
        
        if self.status != self.MODIFIED:
            # What about not initialized
            return
        
        if len(self._current_branch.commitrefs)==0:
            raise Exception, 'This current branch is empty - there is nothing to reset too!!'
        
        cref = self._current_branch.commitrefs[0]
        
        # Do some clean up!
        self._workspace = {}
        self._workspace_root = None
            
            
        # Automatically fetch the object from the hashed dictionary or fetch if needed!
        rootobj = cref.objectroot
        self._workspace_root = rootobj
        
        self._load_links(rootobj)
                
        return rootobj
        
        
    def commit(self, comment=''):
        """
        Commit the current workspace structure
        """
        
        # If the repo is in a valid state - make the commit even if it is up to date
        if self.status == self.MODIFIED or self.status == self.UPTODATE:
            structure={}
            self._workspace_root._recurse_commit(structure)
                                
            cref = self._create_commit_ref(comment=comment)
                
            # Add the CRef to the hashed elements
            cref._recurse_commit(structure)
            
            # set the cref to be readonly
            cref.readonly = True
            
            # Add the cref to the active commit objects - for convienance
            self._commit_index[cref.myid] = cref

            # update the hashed elements
            self._hashed_elements.update(structure)
                            
        else:
            raise Exception, 'Repository in invalid state to commit'
        
        # Like git, return the commit id
        branch = self._current_branch
        return branch.commitrefs.get_link(0).key
            
            
    def _create_commit_ref(self, comment='', date=None):
        """
        @brief internal method to create commit references
        @param comment a string that describes this commit
        @param date the date to associate with this commit. If not given then 
        the current time is used.
        @retval a string which is the commit reference
        """
        # Now add a Commit Ref     
        cref = self.create_wrapped_object(mutable_pb2.CommitRef, addtoworkspace=False)
        
        if not date:
            date = pu.currenttime()
            
        cref.date = date
        
        branch = self._current_branch

        # If this is the first commit to a new repository the current branch is a dummy
        # If it is initialized it is real and we need to link to it!
        if len(branch.commitrefs)==1:
            
            # This branch is real - add it to our ancestors
            pref = cref.parentrefs.add()
            parent = branch.commitrefs[0] # get the parent commit ref
            pref.set_link_by_name('commitref',parent)
            pref.relationship = pref.Parent
        elif len(branch.commitrefs)>1:
            raise Excpetion, 'The Branch is in an invalid state and should have been merged on read!'
        else:
            # This is a new branch and we must add a place for the commit ref!
            branch.commitrefs.add()
        
        # For each branch that we merged from - add a  reference
        for mrgd in self._merged_from:
            pref = cref.parentrefs.add()
            merged_commit = mrgd.commitref # Get the commit ref of the merged item
            pref.set_link_by_name('commitref',merged_commit)
            pref.relationship = pref.MergedFrom
            
        cref.comment = comment
        cref.set_link_by_name('objectroot', self._workspace_root)            
        
        # Update the cref in the branch
        branch.commitrefs.set_link(0,cref)
        
        return cref
    
            
        
    def merge(self, branch=None, commit_id = None, older_than=None):
        """
        merge the named branch in to the current branch
        """
        

        
        
    @property
    def status(self):
        """
        Check the status of the current workspace - return a status
          up to date
          changed
        """
        
        if self._workspace_root:
            if self._workspace_root.modified:
                return self.MODIFIED
            else:
                return self.UPTODATE
        else:
            return self.NOTINITIALIZED
        
        
    def branch(self, nickname=None):
        """
        @brief Create a new branch from the current commit and switch the workspace to the new branch.
        """
        ## Need to check and then clear the workspace???
        #if not self.status == self.UPTODATE:
        #    raise Exception, 'Can not create new branch while the workspace is dirty'
        
        brnch = self.branches.add()    
        brnch.branchkey = pu.create_guid()
        
        if nickname:
            self.branchnicknames[nickname]=brnch.branchkey

        if self._current_branch:
            # Get the linked commit
            
            if len(brnch.commitrefs)>1:
                raise Exception, 'Branch should merge on read. Invalid state!'
            elif len(brnch.commitrefs)==1:                
                cref = self._current_branch.commitrefs[0]
            
                bref = brnch.commitrefs.add()
            
                # Set the new branch to point at the commit
                bref.set_link(cref)
            
            
            # Making a new branch re-attaches to a head!
            if self._detached_head:
                self._workspace_root._set_structure_read_write()
                self._detached_head = False
                
        self._current_branch = brnch
        
    def log_commits(self,branchname):
        
        branch = self.get_branch(branchname)
        log.info('$$ Logging commits on Branch %s $$' % branchname)
        cntr = 0
        for cref in branch.commitrefs:
            cntr+=1
            log.info('$$ Branch Head Commit # %s $$' % cntr)
            
            log.info('Commit: \n' + str(cref))
        
            while len(cref.parentrefs) >0:
                for pref in cref.parentrefs:
                    if pref.relationship == pref.Parent:
                            cref = pref.commitref
                            log.info('Commit: \n' + str(cref))
                            break # There should be only one parent ancestor from a branch
                
        
    def stash(self, name):
        """
        Stash the current workspace for later reference
        """
        
    def create_wrapped_object(self, rootclass, obj_id=None, addtoworkspace=True):        
        
        message = rootclass()
            
        obj = self._wrap_message_object(message, obj_id, addtoworkspace)
            
        return obj
        
    def _wrap_message_object(self, message, obj_id=None, addtoworkspace=True):
        
        if not obj_id:
            obj_id = self.new_id()
        obj = gpb_wrapper.Wrapper(message)
        obj._repository = self
        obj._root = obj
        obj._parent_links = set()
        obj._child_links = set()
        obj._read_only = False
        obj._myid = obj_id
        obj._modified = True     

        if addtoworkspace:
            self._workspace[obj_id] = obj
            
        return obj
        
    def new_id(self):
        """
        This id is a purely local concern - not used outside the local scope.
        """
        self._object_counter += 1
        return str(self._object_counter)
     
    def get_linked_object(self, link):
                
        if link.GPBType != self.LinkClassType:
            raise Exception, 'Illegal argument type in get_linked_object.'
                
                
        if not link.HasField('key'):
            return None
                
        if self._workspace.has_key(link.key):
            return self._workspace.get(link.key)

        elif self._commit_index.has_key(link.key):
            return self._commit_index.get(link.key)

        elif self._hashed_elements.has_key(link.key):
            
            element = self._hashed_elements.get(link.key)
            
            
            if not link.type.package == element.type.package and \
                    link.type.cls == element.type.cls:
                raise Exception, 'The link type does not match the element type!'
            
            obj = self._load_element(element)
            
            if obj.GPBType == self.CommitClassType:
                self._commit_index[obj.myid]=obj
                obj.readonly = True
            else:
                self._workspace[obj.myid]=obj
                obj.readonly = self._detached_head
            return obj
            
        else:
            raise Exception, 'Object not in workbench! You must pull the leaf elements!'
            #return self._workbench.fetch_linked_objects(link)
            
    def _load_links(self, obj, loadleaf=False):
        """
        Load the child objects into the work space
        """        
        if loadleaf:
            
            for link in obj._child_links:
                child = self.get_linked_object(link)  
                self._load_links(child, loadleaf=loadleaf)
        else:
            for link in obj._child_links:
                
                if not link.isleaf:
                    child = self.get_linked_object(link)      
                    self._load_links(child, loadleaf=loadleaf)
        
        
            
    def _load_element(self, element):
        
        #log.debug('_load_element' + str(element))
        
        mysha1 = gpb_wrapper.sha1hex(element.value)
        assert element.key == mysha1, \
            'The sha1 key does not match the value. The data is corrupted! \n' +\
            'Element key %s, Calculated key %s' % (element.key, mysha1)
        
        cls = self._load_class_from_type(element.type)
                                
        # Do not automatically load it into a particular space...
        obj = self.create_wrapped_object(cls, obj_id=element.key, addtoworkspace=False)
            
        obj.ParseFromString(element.value)
        
        # If it is not a leaf element - find its child links
        if not element.isleaf:
            obj._find_child_links()

        obj.modified = False
        
        # Make a note in the element of the child links as well!
        for child in obj._child_links:
            element._child_links.add(child.key)
        
        return obj
        
    def _load_class_from_type(self,ltype):
    
        module = str(ltype.protofile) + '_pb2'
                
        cls_name = str(ltype.cls)
        
        package = str(ltype.package)
        
        log.debug('Loading Class from Type: Package - %s, Module - %s, Class - %s'\
            % (package, module, cls_name))
        
        path = package + '.' + module
        __import__(path)
        
        mod = sys.modules[package+'.'+module]
        
        cls = getattr(mod, cls_name)
                
        return cls
        
        
    def _set_type_from_obj(self, ltype, wrapped_obj):
        """
        This method is a bit of a mess - do we really need it?
        
        It opperates directly on unwrapped GPB objects
        """
            
        obj = wrapped_obj
        if isinstance(obj, gpb_wrapper.Wrapper):
            obj = obj.GPBMessage
            
        gpbtype = gpb_wrapper.set_type_from_obj(obj)
        
        thetype = ltype
        if isinstance(thetype, gpb_wrapper.Wrapper):
            thetype=ltype.GPBMessage
            
        thetype.CopyFrom(gpbtype)
        
        
        
    def set_linked_object(self,field, value):        
        # If it is a link - set a link to the value in the wrapper
        if field.GPBType == field.LinkClassType:
            
            #@Todo Change assertions to Exceptions?
            
            assert value.isroot == True, \
                'You can not set a link equal to part of a gpb composite!'
            
            assert not field.inparents(value), \
                'You can not create a recursive structure - this value is also a parent of the link you are setting.'
            
            
            #Make sure the link is in the objects set of child links
            field._child_links.add(field) # Adds to the fields root wrapper!
            value._parent_links.add(field) 
            
            # If the link is currently set
            if field.key:
                                
                if field.key == value.myid:
                    # Setting it again is a pass...
                    return
                
                
                old_obj = self._workspace.get(field.key,None)
                if old_obj:
                    plinks = old_obj._parent_links
                    plinks.remove(field.key)
                    # If there are no parents left for the object delete it
                    if len(plinks)==0:
                        del self._workspace[field.key]
                    
                
                # Modify the existing link
                field.key = value.myid
                
                # Set the new type
                tp = field.type
                self._set_type_from_obj(tp, value)
                    
            else:
                
                # Set the id of the linked wrapper
                field.key = value.myid
                
                # Set the type
                tp = field.type
                self._set_type_from_obj(tp, value)
                
        else:
            
            raise Exception, 'Can not set a composite field'
            #Over ride Protobufs - I want to be able to set a message directly
        #    field.CopyFrom(value)
        
            