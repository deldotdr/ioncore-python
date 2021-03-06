#!/usr/bin/env python

"""
@file ion/services/dm/preservation/persister.py
@author Paul Hubbard
@author David Stuebe
@author Matt Rodriguez
@date 6/7/10
@brief The persister writes DAP datasets to disk as netcdf files.
@see DAP protocol spec: http://www.opendap.org/pdf/ESE-RFC-004v1.1.pdf
"""


from ion.services.dm.util import dap_tools
import logging
logging = logging.getLogger(__name__)


import os
import tempfile
import shutil
from exceptions import RuntimeError
from pydap.handlers.nca import Handler as ncaHandler

from ion.data import dataobject
from ion.resources.dm_resource_descriptions import DAPMessageObject, StringMessageObject, DictionaryMessageObject

from ion.core.base_process import ProtocolFactory

import uuid
from ion.services.dm.distribution import base_consumer


class PersisterConsumer(base_consumer.BaseConsumer):
    """
    Please update the doc string...
    
    The persister service is responsible for receiving a DAP dataset and
    writing to disk in netcdf format.
    Message protocol/encoding/format:
    * Expect a dictionary with keys for das, dds and dods
    * Since das and dds are multiline strings, they are encoded as json
    * Dods is base64-encoded

    The plan is that writing locally to disk will become writing to a HSM such
    as iRODS that presents a filesystem interface (or file-like-object we can
    hand off to the netcdf.save())

    @note Relies on a single message fitting in memory comfortably.
    @todo Depend on pub-sub
    @todo Notifications of new fileset
    @todo Update fileset directory/registry
    """


    #@defer.inlineCallbacks # If you call a yield inside you need to uncomment the inline callback
    def op_data(self, content, headers, msg):
        """
        @brief: this method is invoked when data arrives off an AMQP Queue
        @param content Message object which could be DAP, Dictionary or String
        @param headers Ignored
        @param msg Used to route the reply, otherwise ignored
        """
        logging.info(self.__class__.__name__ +', MSG Received: ' + str(headers))
        logging.info(self.__class__.__name__ + '; Calling data process!')

        # Keep track of how many messages you got
        self.receive_cnt[headers.get('receiver')] += 1

        # Unpack the message and save it to disk!
        datamessage = dataobject.DataObject.decode(content)
        if isinstance(datamessage, DAPMessageObject):

            dataset = dap_tools.dap_msg2ds(datamessage)            
            # Call preserve DAP data
            fname = self.params['filename']
            
            name = os.path.basename(fname)
            dataset.name = name
            path = fname.replace(name,'')
            
            logging.info( 'name: ' + name)
            logging.info('fname:' + fname)
            logging.info('path:' + path)

            retval = self._save_dap_dataset(dataset,path)
            logging.info("retval from _save_dap_dataset is:"+ str(retval))
            if retval == 1:
                raise RuntimeError("Archive file does not exist")
                
            if retval == 2:
                raise RuntimeError("Problem with NCA handler")
                
                
        elif isinstance(datamessage, (DictionaryMessageObject, StringMessageObject)):
            
            data = datamessage.data
            fname = self.params['filename']
            logging.info("Writing Dictionary or String to " + fname)
            f = open(fname, "w")
            f.write(data)
            f.close()

            #Call preserve dict or string 
            #self._save_string_dataset(data,fname=self.params['filename'])

        else:
            raise RuntimeError("Persister Service received an incompatible message.")
            

        # Later - these will be sent to a historical log for the dataset...
        notification = datamessage.notification
        timestamp = datamessage.timestamp
        

    def _create_nca_configfile(self,base_name):
        """
        @brief: routine that creates a temporary file used by the pydap nca handler.
        @param basename: This is prefix of the filenames that will be appended by 
        the nca handler
        """
        configfile = tempfile.NamedTemporaryFile()
        configfile.write("[dataset]")
        configfile.write(os.linesep)
        configfile.write("name=append")
        configfile.write(os.linesep)
        configfile.write("match=" + base_name + "_*.nc")
        configfile.write(os.linesep)
        configfile.write("axis=time")
        configfile.write(os.linesep)
        configfile.flush()
        return configfile

    def _save_dap_dataset(self, dataset, path):
        """
        @brief save the dataset as a netcdf file or append to an existing file
        @param dataset a pydap dataset
        @param fname the name of the file to write the pydap dataset,
        fname must use an absolute path
        """
        
        fname = dataset.name
        fname = os.path.join(path, fname)
        
        if '%2Enc' in fname:
            fname = fname.replace('%2Enc','.nc')
        
        elif not '.nc' in fname:
            fname = ".".join((fname, "nc"))
        
        
        logging.info("running _save_dap_dataset, fname=%s" % fname)
        try:
            os.stat(fname)
        except OSError:
            logging.info("Archive file does not exist")
            # Use return value - or throw an exception?
            return 1
        
        #Check to see if the file exists but is empty. 
        if os.path.getsize(fname) == 0:
            # Write the data to a new file
            logging.info("Archive file exists, but is empty")
            dap_tools.write_netcdf_from_dataset(dataset, fname)
            return 0
        else:
            #The file exists and is not empty, append the contents
            
            tmp_file_base = os.path.join(path, str(uuid.uuid4())[:8])
            
            tmp_file_0 = tmp_file_base + '_0.nc'
            
            shutil.copy(fname, tmp_file_0)
            
            tmp_file_1 = tmp_file_base + '_1.nc'
            dap_tools.write_netcdf_from_dataset(dataset, tmp_file_1)
            
            logging.info("Write new dataset to the file")
            configfile = self._create_nca_configfile(tmp_file_base)    
            logging.info("Initializing nca handler")
            h = ncaHandler(configfile.name)
            try:
                ds = h.parse_constraints({'pydap.ce':(None,None)})
            except:
                logging.exception("problem using append handler")
                # Use return value or exception?
                os.remove(tmp_file_1)
                os.remove(tmp_file_0)
                return 2
        
            logging.info("Created new netcdf dataset")
            dap_tools.write_netcdf_from_dataset(ds, tmp_file_base + 'agg.nc')
            shutil.move(tmp_file_base + 'agg.nc', fname)

            configfile.close()
            os.remove(tmp_file_1)
            os.remove(tmp_file_0)
        
            return 0
        
        
    '''
    # Must be called op_data
    @defer.inlineCallbacks
    def op_persist_dap_dataset(self, content, headers, msg): 
        """
        @brief top-level routine to persist a dataset.
        @param content Message with das, dds and dods keys
        @param headers Ignored
        @param msg Used to route the reply, otherwise ignored
        @retval RPC message via reply_ok/reply_err
        """
        logging.info('called to persist a dap dataset!')

        assert(isinstance(content, dict))

        try:
            rc = self._save_no_xmit(content)
        except KeyError:
            yield self.reply_err(msg, {'value':'Missing headers'}, {})
            defer.returnValue(None)
        if rc:
            yield self.reply_err(msg, {'value': 'Error saving!'}, {})
            defer.returnValue(None)

        yield self.reply_ok(msg)
    
    # Must also be called op_data?
    @defer.inlineCallbacks
    def op_append_dap_dataset(self, content, headers, msg): 
        """
        @brief routine to append to an existing dataset which is a netcdf file
        @param content Message with dataset name, pattern, das, dds and dods keys
        The dataset name is mapped to a file that will be used to persist the dataset
        The pattern is used to match all of the files that will be appended
        @param headers Ignored
        @param msg Used to route the reply, otherwise ignored
        @retval RPC message via reply_ok/reply_err
        """
        logging.info('called to append a dap dataset!')
        
        assert(isinstance(content, dict))
        
        try:
            self.op_persist_dap_dataset(content, headers, msg)
        except:
            yield self.reply_err(msg, {'value': 'Problem with persisting new dataset'}, {})
            defer.returnValue(None)
        dataset = content["dataset"]    
        dsname = generate_filename(dataset)
        pattern = content["pattern"]
        
        logging.info('using netcdf file matching pattern: ' + pattern)
        try:
            logging.info("calling _append_no_xmit ")
            rc = self._append_no_xmit(dsname, pattern)
            logging.info("returned from _append_no_xmit with rc ", rc)
        except:
            yield self.reply_err(msg, {'value':'Problem appending the dataset'}, {})
            defer.returnValue(None)
            
        yield self.reply_ok(msg)

        
    def _append_no_xmit(self, dsname, pattern, local_dir=None):
        """
        @brief Appends netcdf files together. 
        @param dsname, the name of the file that contains the 
        @param pattern a pattern used to match netcdf files to append
         
        """
        configfile = tempfile.NamedTemporaryFile()
        configfile.write("[dataset]")
        configfile.write(os.linesep)
        configfile.write("name=append")
        configfile.write(os.linesep)
        configfile.write("match="+ pattern)
        configfile.write(os.linesep)
        configfile.write("axis=time")
        configfile.write(os.linesep)
        configfile.flush()    
        logging.info("Initializing nca handler")
        h = ncaHandler(configfile.name)
        try:
            ds = h.parse_constraints({'pydap.ce':(None,None)})
        except:
            logging.exception("problem using append handler")
            return 2
        
        logging.info("Created new netcdf dataset")
        try:
            
            logging.info("saving netcdf file")
            #It needs to save the file to a new file name, I have arbitrarily chosen
            #to make the file the same as the first file name with the suffix _append
            netcdf.save(ds, dsname+ "_append")
        except UnicodeDecodeError, ude:
            logging.exception('save error: %s ' % ude)
            return 1
        
        configfile.close()
        
    
    def _save_no_xmit(self, content, local_dir=None):
        """
        @brief Parse message into decodable objects: DAS, DDS, data.
        Then calls _save_dataset to to the pydap->netcdf step.
        @param content Dictionary with dds, das, dods keys
        @param local_dir If set, destination directory (e.g. iRODS)
        @retval Return value from _save_dataset
        @note if no local_dir, set from config file via generate_filename
        """
        try:
            logging.debug('Decoding %d byte dataset...' % len(str(content)))
            dds = json.loads(str(content['dds']))
            das = json.loads(str(content['das']))
            dods = base64.b64decode(content['dods'])
            source_url = content['source_url']
            logging.debug('Decoded dataset OK')
        except KeyError, ke:
            logging.error('Unable to find required fields in dataset!')
            raise ke

        logging.debug('DAS snippet: ' + das[:80])
        logging.debug('DDS snippet: ' + dds[:80])

        return(self._save_dataset(das, dds, dods, source_url, local_dir=local_dir))

    def _save_dataset(self, das, dds, dods, source_url, local_dir=None):
        """
        @brief Does the conversion from das+dds+dods into pydap objects and
        thence to a netcdf file. Mostly pydap code, though we do brand/annotate
        the dataset in the NC_GLOBAL attribute. (Experimental feature)
        @param das DAS metadata, as returned from the server
        @param dds DDS metadata, as returned from the server
        @param dods DODS (actual data), XDR encoded, as returned from the server
        @param source_url Original URL, used as key in dataset registry
        @param local_dir If set, destination directory
        """
        das = str(das)
        logging.debug('Starting creation of pydap objects')
        dataset = DDSParser(dds).parse()
        dataset = DASParser(das, dataset).parse()

        """
        Tag global attributes with cache info
        @todo Design decision - what goes into per-file metadata?
        @note This is purely OOI code - not pydap at all.
        """
        dataset.attributes['NC_GLOBAL']['ooi-download-timestamp'] = time.asctime()
        dataset.attributes['NC_GLOBAL']['ooi-source-url'] = source_url

        # Back to pydap code - this block is from open_url in client.py
        # Remove any projections from the url, leaving selections.
        scheme, netloc, path, query, fragment = urlsplit(source_url)
        projection, selection = parse_qs(query)
        url = urlunsplit(
                (scheme, netloc, path, '&'.join(selection), fragment))

        # Set data to a Proxy object for BaseType and SequenceType. These
        # variables can then be sliced to retrieve the data on-the-fly.
        for var in walk(dataset, BaseType):
            var.data = ArrayProxy(var.id, url, var.shape)
        for var in walk(dataset, SequenceType):
            var.data = SequenceProxy(var.id, url)

        # Apply the corresponding slices.
        projection = fix_shn(projection, dataset)
        for var in projection:
            target = dataset
            while var:
                token, slice_ = var.pop(0)
                target = target[token]
                if slice_ and isinstance(target.data, VariableProxy):
                    shape = getattr(target, 'shape', (sys.maxint,))
                    target.data._slice = fix_slice(slice_, shape)

        # This block is from open_dods in client.py
        dds, xdrdata = dods.split('\nData:\n', 1)
        dataset.data = DapUnpacker(xdrdata, dataset).getvalue()

        logging.debug('pydap object creation complete')
        fname = generate_filename(source_url, local_dir=local_dir)
        logging.info('Saving DAP dataset "%s" to "%s"' % (source_url, fname))

        try:
            netcdf.save(dataset, fname)
        except UnicodeDecodeError, ude:
            logging.exception('save error: %s ' % ude)
            return 1
 '''   
# Must change name after refactor
factory = ProtocolFactory(PersisterConsumer)


'''
There is no client for a consumer...
class PersisterClient(BaseServiceClient): # Not really needed - consumers don't have clients
    def __init__(self, proc=None, **kwargs):
        if not 'targetname' in kwargs:
            kwargs['targetname'] = 'persister'
        BaseServiceClient.__init__(self, proc, **kwargs)

    @defer.inlineCallbacks
    def persist_dap_dataset(self, dap_message):
        """
        @brief Invoke persister, assumes a single dataset per message
        @param dap_message Message with das/dds/dods in das/dds/dods keys
        @retval ok or error via rpc mechanism
        """
        yield self._check_init()

        (content, headers, msg) = yield self.rpc_send('persist_dap_dataset',
                                                      dap_message)
        
        logging.debug('dap persist returns: ' + str(content))
        defer.returnValue(str(content))
        
    @defer.inlineCallbacks   
    def append_dap_dataset(self, dataset, pattern, dap_message):
        """
        @brief Append to an existing dataset, new data from a dap message
        @param dataset, a logical name of the dataset, this name is mapped to a file name
        @param dap_message Message with das/dds/dods in das/dds/dods keys 
        @retval ok or error via rpc mechanism
        """
        yield self._check_init()
        dap_message.update({'dataset': dataset})
        dap_message.update({'pattern': pattern})
        (content, headers, meg) = yield self.rpc_send('append_dap_dataset', 
                                                      dap_message)
        
        logging.debug('dap append returns: ' + str(content))
        defer.returnValue(str(content))
'''


#
