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

from nose.tools import eq_, ok_

from vbench.utils import multires_order

def test_multires_order():
    r = [str(x) for x in range(5)]
    eq_(multires_order(tuple(r)), ('0', '2', '4', '1', '3'))
    eq_(multires_order(r), ['0', '2', '4', '1', '3'])
    import numpy as np
    oa = multires_order(np.array(r))
    ok_(isinstance(oa, np.ndarray))
    ok_(np.all(oa == np.array(['0', '2', '4', '1', '3'])))

    for n in range(123):
        o = multires_order(n)
        # print n, o[-10:]
        eq_(len(o), n)
        eq_(len(set(o)), n) #  all are unique
        if n > 0: eq_(o[0], 0)
        if n > 1: ok_(o[1] in [n//2,n//2-1])
        if n > 2: eq_(o[2], n-1)
        if n > 8: ok_(o[3] != 1)          # we must not get to the 1st yet
        if n > 3: ok_(o[-1] in [n-2, n-3])   # end should be very close to last ones
