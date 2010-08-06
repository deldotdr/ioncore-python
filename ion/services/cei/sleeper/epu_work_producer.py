import logging
import random
from twisted.internet import defer
from twisted.internet.task import LoopingCall
from twisted.web import server, resource
from twisted.internet import reactor
from magnet.spawnable import Receiver
from ion.services.base_service import BaseService, BaseServiceClient
from ion.core.base_process import ProtocolFactory
import Queue
import uuid
import ion.services.cei.cei_events as cei_events

logging.basicConfig(level=logging.DEBUG)
logging.debug('Loaded: '+__name__)

class EPUWorkProducer(BaseService):
    """EPU Work Producer.
    """
    declare = BaseService.service_declare(name='epu_work_producer', version='0.1.0', dependencies=[])

    def slc_init(self):
        self.queue_name_work = self.get_scoped_name("system", self.spawn_args["queue_name_work"])
        self.web_resource = Sidechannel()
        reactor.listenTCP(8000, server.Site(self.web_resource))
        self.work_produce_loop = LoopingCall(self.work_seek)
        self.work_produce_loop.start(1, now=False)

    @defer.inlineCallbacks
    def work_seek(self):
        try:
            while True:
                job = self.web_resource.queue.get(block=False)
                if job == None:
                    return
                
                yield self.send(self.queue_name_work, 'work', {"work_amount":job.length, "batchid":job.batchid, "jobid":job.jobid})
                
                # events need dict support first
                #extra = {"batchid":job.batchid, "jobid":job.jobid, "work_amount":job.length}
                cei_events.event("workproducer", "JOBSENT", logging)
                
        except Queue.Empty:
            return

# Direct start of the service as a process with its default name
factory = ProtocolFactory(EPUWorkProducer)

class SleepJob:
    def __init__(self, jobid, batchid, length):
        self.jobid = jobid
        self.batchid = batchid
        self.length = int(length)

# Sidechannel access to tell service what to do
class Sidechannel(resource.Resource):
    isLeaf = True
    def __init__(self):
        self.queue = Queue.Queue()
        
    def render_GET(self, request):
        parts = request.postpath
        if parts[-1] == "":
            parts = parts[:-1]
        if len(parts) != 3:
            request.setResponseCode(500, "expecting three 'args', /batchid/#jobs/#sleepsecs")
            return
        
        try:
            batchid = parts[0]
            jobnum = int(parts[1])
            secperjob = int(parts[2])
        except Exception,e:
            request.setResponseCode(500, "expecting three args, /batchid/#jobs/#sleepsecs, those should be INTEGERS..  %s" % e)
            return

        sleepjobs = []
        for i in range(jobnum):
            sleepjobs.append(SleepJob(i, batchid, secperjob))
        
        for job in sleepjobs:
            self.queue.put(job)
        
        logging.debug("enqueued %d jobs with %d sleep seconds" % (jobnum, secperjob))
        return "<html>Success.</html>\n"
