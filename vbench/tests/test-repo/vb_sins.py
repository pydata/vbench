#emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
from vbench.benchmark import Benchmark

setup = """\
from vb_common import *
"""

# Separate benchmark
vb1000 = Benchmark("manysins(1000)", setup=setup+"from vbenchtest.m1 import manysins")

# List of the benchmarks
vb_collection = [Benchmark("manysins(%d)" % n ,
                           setup=setup+"from vbenchtest.m1 import manysins")
                 for n in [100, 2000]]