
from twisted.internet import defer

from ion.core import ioninit
CONF = ioninit.config(__name__)
from ion.util.itv_decorator import itv
from ion.test.iontest import IonTestCase
from ion.util import procutils as pu
import ion.util.ionlog
log = ion.util.ionlog.getLogger(__name__)

class SkipAlong(IonTestCase):

    @defer.inlineCallbacks
    def setUp(self):
        yield self._start_container()

    @defer.inlineCallbacks
    def tearDown(self):
        yield self._stop_container()

    def test_1(self):
        pass
    def test_12(self):
        pass
    def test_13(self):
        pass
    def test_14(self):
        pass
    def test_15(self):
        pass
    def test_16(self):
        pass
    def test_17(self):
        pass
    def test_18(self):
        pass
    def test_19(self):
        pass

class SkipAlongDeferred(SkipAlong):
    @defer.inlineCallbacks
    def test_1(self):
        yield pu.asleep(.1)
    @defer.inlineCallbacks
    def test_12(self):
        yield pu.asleep(.1)
    @defer.inlineCallbacks
    def test_13(self):
        yield pu.asleep(.1)
    @defer.inlineCallbacks
    def test_14(self):
        yield pu.asleep(.1)
    @defer.inlineCallbacks
    def test_15(self):
        yield pu.asleep(.1)
    @defer.inlineCallbacks
    def test_16(self):
        yield pu.asleep(.1)
    @defer.inlineCallbacks
    def test_17(self):
        yield pu.asleep(.1)
    @defer.inlineCallbacks
    def test_18(self):
        yield pu.asleep(.1)
    @defer.inlineCallbacks
    def test_19(self):
        yield pu.asleep(.1)

class SkipAlongItv(SkipAlong):

    @itv(CONF) 
    def test_1(self):
        pass
    @itv(CONF) 
    def test_12(self):
        pass
    @itv(CONF) 
    def test_13(self):
        pass
    @itv(CONF) 
    def test_14(self):
        pass
    @itv(CONF) 
    def test_15(self):
        pass
    @itv(CONF) 
    def test_16(self):
        pass
    @itv(CONF) 
    def test_17(self):
        pass
    @itv(CONF) 
    def test_18(self):
        pass
    @itv(CONF) 
    def test_19(self):
        pass

class SkipAlongDeferredItv(SkipAlong):
    @itv(CONF) 
    @defer.inlineCallbacks
    def test_1(self):
        yield pu.asleep(.1)
    @itv(CONF) 
    @defer.inlineCallbacks
    def test_12(self):
        yield pu.asleep(.1)
    @itv(CONF) 
    @defer.inlineCallbacks
    def test_13(self):
        yield pu.asleep(.1)
    @itv(CONF) 
    @defer.inlineCallbacks
    def test_14(self):
        yield pu.asleep(.1)
    @itv(CONF) 
    @defer.inlineCallbacks
    def test_15(self):
        yield pu.asleep(.1)
    @itv(CONF) 
    @defer.inlineCallbacks
    def test_16(self):
        yield pu.asleep(.1)
    @itv(CONF) 
    @defer.inlineCallbacks
    def test_17(self):
        yield pu.asleep(.1)
    @itv(CONF) 
    @defer.inlineCallbacks
    def test_18(self):
        yield pu.asleep(.1)
    @itv(CONF) 
    @defer.inlineCallbacks
    def test_19(self):
        yield pu.asleep(.1)
 
