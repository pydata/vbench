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

from math import ceil

def multires_order(n):
    """Provide order of indexes slowly detailing into the history

    Often it is desirable to order investigation of events in history
    at "multiple resolutions".  So at first we get a glimpse of the
    history at 3 points (first, middle, last) and then get deeper by
    making our step twice smaller at each "resolution".  So for
    e.g. n=9 order of indexes for such inspection would be [0, 4, 8,
    2, 6, 1, 5, 3, 7] .

    It should remind (if not being identical) to traversing the binary
    heap associated with a list of indexes: as if we first took at
    corners and then go layer by layer including the depth.

    Current procedure is a very sloppy implementation, so inefficient
    in general but good enough for real use (e.g. 26.6ms for n=10000)
    """

    if isinstance(n, list) or isinstance(n, tuple):
       return n.__class__(n[i] for i in multires_order(len(n)))
    elif 'ndarray' in str(type(n)):
       return n[multires_order(len(n))]
    assert(isinstance(n, int))

    out = []
    # to speed up checks, we will consume some memory but mark
    # each index whenever we add it to out
    seen = [False] * n
    for i in xrange(1, n):
        # fp step so we could point to the 0th, middle, last
        # on the first run
        step = float(n-1)/(2*i)
        gotnew = False
        for k in xrange(int(ceil(float(n)/step))):
            idx = int(k*step)
            if not seen[idx]: # in seen:
               out.append(idx)
               seen[idx] = True
               gotnew = True
        if not gotnew:
            #print "D: exiting from loop with i=%d n=%d" % (i, n)
            break
    if len(out) != n:
        # Fill in the holes -- some might still be missing, so
        # add them at the end
        # print "D: %d are still missing" % (n-len(out))
        out.extend([i for i in range(n) if not seen[i]])
    assert(set(out) == set(range(n)))
    return out
