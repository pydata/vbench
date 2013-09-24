#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
#ex: set sts=4 ts=4 sw=4 noet:
#------------------------- =+- Python script -+= -------------------------
"""
 COPYRIGHT: Yaroslav Halchenko 2013

 LICENSE: MIT

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
"""

__author__ = 'Yaroslav Halchenko'
__copyright__ = 'Copyright (c) 2013 Yaroslav Halchenko'
__license__ = 'MIT'

from nose.tools import eq_, assert_greater

import time
from vbench.benchmark import magic_timeit

def test_magic_timeit():
    env = {'sleep': time.sleep}

    # neither repeat nor ncalls provided
    # just a shortcut
    def timeit_sleepms(**kwargs):
        # we target 200ms runtime, and all the checks are quite loose
        # in terms of timing etc ATM so they do not fail on any busy
        # box
        return magic_timeit({'sleep': time.sleep }, "sleep(1e-3)",
                            target_timing=0.2, force_ms=True, **kwargs)

    t1 = timeit_sleepms()              # all defaults
    assert_greater(2, t1['timing'])    # we must not be entirely off
    assert_greater(t1['repeat'], 10) # there should have been at least 10 repeats
    assert_greater(t1['loops'], 10) # there should have been at least 10 loops
    eq_(t1['units'], 'ms') # we forced ms

    t1 = timeit_sleepms(repeat=3)      # provide repeat
    assert_greater(2, t1['timing'])    # we must not be entirely off
    eq_(t1['repeat'], 3)               # there must be 3 repeats
    assert_greater(t1['loops'], 20)    # there should have been at least 20 loops
    eq_(t1['units'], 'ms') # we forced ms

    t1 = timeit_sleepms(ncalls=5)      # provide ncalls
    assert_greater(2, t1['timing'])    # we must not be entirely off
    assert_greater(t1['repeat'], 20)   # there should have been at least 20 repeats
    eq_(t1['loops'], 5)                # there must be 5 loops
    eq_(t1['units'], 'ms') # we forced ms

    t1 = timeit_sleepms(repeat=6, ncalls=5)      # provide both ncalls and repeat
    assert_greater(2, t1['timing'])    # we must not be entirely off
    eq_(t1['repeat'], 6)               # there must be 6 repeats
    eq_(t1['loops'], 5)                # there must be 5 loops
    eq_(t1['units'], 'ms') # we forced ms
