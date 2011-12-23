# pylint: disable=W0122

from cStringIO import StringIO

import cProfile
import pstats

import gc
import hashlib
import time
import traceback

class Benchmark(object):

    def __init__(self, code, setup, ncalls=None, cleanup=None,
                 name=None, description=None, start_date=None):
        self.code = code
        self.setup = setup
        self.cleanup = cleanup or ''
        self.ncalls = ncalls
        self.name = name
        self.description = description
        self.start_date = start_date

    def __repr__(self):
        return "Benchmark('%s')" % self.name

    def _setup(self):
        ns = globals().copy()
        exec self.setup in ns
        return ns

    def _cleanup(self, ns):
        exec self.cleanup in ns

    @property
    def checksum(self):
        return hashlib.md5(self.setup + self.code + self.cleanup).hexdigest()

    def profile(self, ncalls):
        prof = cProfile.Profile()
        ns = self._setup()

        code = compile(self.code, '<f>', 'exec')
        def f(*args, **kw):
            for i in xrange(ncalls):
                exec code in ns
        prof.runcall(f)

        self._cleanup(ns)

        return pstats.Stats(prof).sort_stats('cumulative')

    def get_results(self, db_path):
        from vbench.db import BenchmarkDB
        db = BenchmarkDB.get_instance(db_path)
        return db.get_benchmark_results(self.checksum)

    def run(self):
        ns = self._setup()

        try:
            result = magic_timeit(ns, self.code, ncalls=self.ncalls,
                                  force_ms=True)
            result['succeeded'] = True
        except:
            buf = StringIO()
            traceback.print_exc(file=buf)
            result = {'succeeded' : False, 'traceback' : buf.getvalue()}
        
        self._cleanup(ns)
        return result

    def _run(self, ns, ncalls, disable_gc=False):
        if ncalls is None:
            ncalls = self.ncalls
        code = self.code
        if disable_gc:
            gc.disable()

        start = time.clock()
        for _ in xrange(ncalls):
            exec code in ns

        elapsed = time.clock() - start
        if disable_gc:
            gc.enable()

        return elapsed

    def to_rst(self, image_path=None):
        output = """**Benchmark setup**

.. code-block:: python

%s

**Benchmark statement**

.. code-block:: python

%s

""" % (indent(self.setup), indent(self.code))

        if image_path is not None:
            output += ("**Performance graph**\n\n.. image:: %s"
                       "\n   :width: 6in" % image_path)

        return output

    def plot(self, db_path, label=None, ax=None, title=True):
        import matplotlib.pyplot as plt
        from matplotlib.dates import MonthLocator, DateFormatter

        results = self.get_results(db_path)

        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)

        results['timing'].plot(ax=ax, label=label)

        ax.set_ylabel('milliseconds')
        ax.set_xlabel('Date')


        ylo, yhi = ax.get_ylim()

        if ylo < 1:
            ax.set_ylim([0, yhi])

        formatter = DateFormatter("%b %Y")
        ax.xaxis.set_major_locator(MonthLocator())
        ax.xaxis.set_major_formatter(formatter)
        ax.autoscale_view(scalex=True)

        if title:
            ax.set_title(self.name)

        return ax


def indent(string, spaces=4):
    dent = ' ' * spaces
    return '\n'.join([dent + x for x in string.split('\n')])

class BenchmarkSuite(object):

    pass

# Modified from IPython project, http://ipython.org

def magic_timeit(ns, stmt, ncalls=None, force_ms=False):
    """Time execution of a Python statement or expression

    Usage:\\
      %timeit [-n<N> -r<R> [-t|-c]] statement

    Time execution of a Python statement or expression using the timeit
    module.

    Options:
    -n<N>: execute the given statement <N> times in a loop. If this value
    is not given, a fitting value is chosen.

    -r<R>: repeat the loop iteration <R> times and take the best result.
    Default: 3

    -t: use time.time to measure the time, which is the default on Unix.
    This function measures wall time.

    -c: use time.clock to measure the time, which is the default on
    Windows and measures wall time. On Unix, resource.getrusage is used
    instead and returns the CPU user time.

    -p<P>: use a precision of <P> digits to display the timing result.
    Default: 3


    Examples:

      In [1]: %timeit pass
      10000000 loops, best of 3: 53.3 ns per loop

      In [2]: u = None

      In [3]: %timeit u is None
      10000000 loops, best of 3: 184 ns per loop

      In [4]: %timeit -r 4 u == None
      1000000 loops, best of 4: 242 ns per loop

      In [5]: import time

      In [6]: %timeit -n1 time.sleep(2)
      1 loops, best of 3: 2 s per loop


    The times reported by %timeit will be slightly higher than those
    reported by the timeit.py script when variables are accessed. This is
    due to the fact that %timeit executes the statement in the namespace
    of the shell, compared with timeit.py, which uses a single setup
    statement to import function or create variables. Generally, the bias
    does not matter as long as results from timeit.py are not mixed with
    those from %timeit."""

    import timeit
    import math

    units = ["s", "ms", 'us', "ns"]
    scaling = [1, 1e3, 1e6, 1e9]

    timefunc = timeit.default_timer

    repeat = timeit.default_repeat
    timer = timeit.Timer(timer=timefunc)
    # this code has tight coupling to the inner workings of timeit.Timer,
    # but is there a better way to achieve that the code stmt has access
    # to the shell namespace?

    src = timeit.template % {'stmt': timeit.reindent(stmt, 8),
                             'setup': "pass"}
    # Track compilation time so it can be reported if too long
    # Minimum time above which compilation time will be reported
    code = compile(src, "<magic-timeit>", "exec")

    exec code in ns
    timer.inner = ns["inner"]

    if ncalls is None:
        # determine number so that 0.2 <= total time < 2.0
        number = 1
        for _ in range(1, 10):
            if timer.timeit(number) >= 0.3:
                break
            number *= 10
    else:
        number = ncalls

    best = min(timer.repeat(repeat, number)) / number

    if force_ms:
        order = 1
    else:
        if best > 0.0 and best < 1000.0:
            order = min(-int(math.floor(math.log10(best)) // 3), 3)
        elif best >= 1000.0:
            order = 0
        else:
            order = 3

    return {'loops' : number,
            'repeat' : repeat,
            'timing' : best * scaling[order],
            'units' : units[order]}

def gather_benchmarks(ns):
    return [v for v in ns.values() if isinstance(v, Benchmark)]
