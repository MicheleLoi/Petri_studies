"""Offline timing tests. No credentials or network calls."""
import unittest
from paced_runner import PacedTransport

class Clock:
    def __init__(self): self.value = 0
    def now(self): return self.value
    def sleep(self, seconds): self.value += seconds

class Inner:
    def __init__(self, clock): self.clock=clock; self.calls=[]; self.fail=False
    def prepare(self, model): self.calls.append(('prepare',self.clock.now())); return 'auth'
    def send(self, spec, auth, timeout):
        self.calls.append(('send',self.clock.now(),spec,auth,timeout))
        self.clock.sleep(2)
        if self.fail: raise ConnectionError('synthetic')
        return {'http_status':200}

class PacingTests(unittest.TestCase):
    def setUp(self):
        self.clock=Clock(); self.inner=Inner(self.clock)
        self.p=PacedTransport(self.inner,monotonic=self.clock.now,sleeper=self.clock.sleep)
    def test_success_gap_and_unchanged_arguments(self):
        self.p.prepare('jev'); self.p.send({'a':1},'auth',(1,2)); self.p.prepare('jev')
        self.assertEqual(self.clock.now(),62)
        self.assertEqual(self.inner.calls[1],('send',0,{'a':1},'auth',(1,2)))
    def test_failure_also_paced(self):
        self.inner.fail=True
        with self.assertRaises(ConnectionError): self.p.send({},'auth',(1,2))
        self.p.prepare('jev'); self.assertEqual(self.clock.now(),62)
    def test_resumed_wait(self):
        p=PacedTransport(self.inner,35,monotonic=self.clock.now,sleeper=self.clock.sleep)
        p.prepare('jev'); self.assertEqual(self.clock.now(),35)
    def test_already_elapsed_does_not_wait_again(self):
        self.p.send({},'auth',(1,2)); self.clock.sleep(90); self.p.prepare('jev')
        self.assertEqual(self.clock.now(),92)

if __name__=='__main__': unittest.main()
