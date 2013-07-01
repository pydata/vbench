#emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
from vbench.benchmark import Benchmark

# We do not care about precision, so ncalls is set low
# Separate benchmark
a_single_sin = Benchmark("manysins(1)", setup="from vbenchtest.m1 import manysins", ncalls=2)
