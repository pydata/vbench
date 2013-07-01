#emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
from vbench.benchmark import Benchmark

setup = """\
from vb_common import *
"""

# We do not care about precision, so ncalls is set low

# Separate benchmark
vb1000 = Benchmark("manysins(1000)", setup=setup+"from vbenchtest.m1 import manysins",
                   ncalls=2)

# List of the benchmarks
vb_collection = [Benchmark("manysins(%d)" % n ,
                           setup=setup+"from vbenchtest.m1 import manysins",
                           name="manysins(%d)_from_collection" % (n,),
                           ncalls=2)
                 for n in [100, 2000]]
