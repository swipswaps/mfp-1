from mfp.rpc_wrapper import RPCWrapper, rpcwrap
from mfp.rpc_worker import RPCServer
import time
from unittest import TestCase


class WrappedClass(RPCWrapper):
    def __init__(self, arg1, **kwargs):
        self.arg = arg1
        RPCWrapper.__init__(self, arg1, **kwargs)

    @rpcwrap
    def retarg(self):
        return self.arg

    @rpcwrap
    def setarg(self, value):
        self.arg = value

    @rpcwrap
    def error_method(self):
        return 1 / 0


class Pinger(RPCWrapper):
    def __init__(self, volleys):
        RPCWrapper.__init__(self, volleys)
        if Pinger.local:
            self.volleys = volleys
            self.ponger = None
            if self.volleys > 0:
                self.ponger = Ponger(volleys - 1)

    @rpcwrap
    def ping(self):
        if self.ponger:
            return self.ponger.pong()
        else:
            return "PING"


class Ponger(RPCWrapper):
    def __init__(self, volleys):
        RPCWrapper.__init__(self, volleys)
        if Ponger.local:
            self.volleys = volleys
            self.pinger = None
            if self.volleys > 0:
                self.pinger = Pinger(volleys - 1)

    @rpcwrap
    def pong(self):
        if self.pinger:
            return self.pinger.ping()
        else:
            return "PONG"

reverse_value = None


class ReverseClass(RPCWrapper):
    @rpcwrap
    def reverse(self):
        global reverse_value
        print "Reverse:", reverse_value
        return reverse_value

    @rpcwrap
    def fail(self):
        return 1 / 0


class ReverseActivatorClass(RPCWrapper):
    @rpcwrap
    def reverse(self):
        print "Activator: ", ReverseActivatorClass.local, ReverseClass.local
        o = ReverseClass()
        print "Activator:", o
        return o.reverse()


def rpcinit(*_):
    # RPCWorkerTests slave init
    WrappedClass.local = True


class RPCTests(TestCase):
    def setUp(self):
        print "==================="
        print "setup started"
        self.server = RPCServer("test", rpcinit)
        self.server.start()
        RPCWrapper.pipe = self.server.pipe
        self.server.serve(WrappedClass)
        print self.server
        print "-------------------"
        time.sleep(0.2)

    def test_local(self):
        '''test_local: local calls on a RPCWrapper subclass work'''
        o = WrappedClass("hello")
        print "test_local: created", o
        o.local = True
        self.assertEqual(o.retarg(), "hello")
        o.setarg("goodbye")
        self.assertEqual(o.retarg(), "goodbye")

    def test_remote(self):
        '''test_remote: calls on remote objects work'''
        o = WrappedClass(123.45)
        self.assertNotEqual(o.rpcid, None)
        try:
            self.assertEqual(o.retarg(), 123.45)
            o.setarg(dict(x=1, y=2))
            self.assertEqual(o.retarg(), dict(x=1, y=2))
        except RPCWrapper.MethodFailed, e:
            print '-------------------------'
            print e.traceback
            print '-------------------------'
            assert 0

    def test_badmethod(self):
        '''test_badmethod: failed method should raise MethodFailed'''
        failed = 0
        try:
            o = WrappedClass('foo')
            o.error_method()
        except RPCWrapper.MethodFailed, e:
            failed = 1
            print e.traceback

        self.assertEqual(failed, 1)

    def tearDown(self):
        self.server.finish()


def winit(*args):
    # RPCWorkerTests slave init
    WrappedClass.local = True
    ReverseActivatorClass.local = True
    ReverseClass.local = False
    Ponger.local = True
    Pinger.local = False


class RPCServerTests(TestCase):
    def setUp(self):
        print "==================="
        print "setup started"
        self.server = RPCServer("worker", winit)
        self.server.start()
        RPCWrapper.pipe = self.server.pipe
        self.server.serve(ReverseActivatorClass)
        self.server.serve(WrappedClass)
        self.server.serve(Ponger)

        ReverseClass.local = True
        Pinger.local = True
        Ponger.local = False
        print self.server, self.server.pipe
        print "--------------------"
        time.sleep(0.2)

    def test_create_from_slave(self):
        '''test_create_from_slave: slave creates a local object on master'''
        global reverse_value
        o1 = ReverseActivatorClass()
        reverse_value = 'hello'
        self.assertEqual(o1.reverse(), 'hello')

        reverse_value = 'goodbye'
        self.assertEqual(o1.reverse(), 'goodbye')

    def test_obj_create(self):
        '''test_obj_create: RPCWorker can create objects'''
        o = WrappedClass('lalala')
        failed = 0
        try:
            o.error_method()
        except RPCWrapper.MethodFailed, e:
            failed = 1
        self.assertEqual(failed, 1)
        self.assertEqual(o.retarg(), 'lalala')

    def test_ping_pong_0(self):
        a = Pinger(0)
        b = Ponger(0)
        self.assertEqual(a.ping(), "PING")
        self.assertEqual(b.pong(), "PONG")

    def test_ping_pong_1(self):
        a = Pinger(1)
        self.assertEqual(a.ping(), "PONG")

    def test_ping_pong_2(self):
        a = Pinger(2)
        self.assertEqual(a.ping(), "PING")

    def test_ping_pong_20(self):
        a = Pinger(20)
        print "================== Pinger constructed."
        self.assertEqual(a.ping(), "PING")

    def tearDown(self):
        self.server.finish()