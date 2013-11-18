# pylint: disable=W0122

from cStringIO import StringIO

import cProfile
try:
    import pstats
except ImportError:
    # pstats.py was not available in python 2.6.6 distributed on Debian squeeze
    # systems and was included only starting from 2.6.7-2.  That is why import
    # from a local copy
    import _pstats as pstats

import gc
import hashlib
import re
import time
import traceback
import inspect

import numpy as np

# from pandas.util.testing import set_trace

import logging
log = logging.getLogger('vb.benchmark')


class Benchmark(object):

    def __init__(self, code, setup, ncalls=None, repeat=3, cleanup=None,
                 name=None, module_name=None, description=None, start_date=None,
                 logy=False, prereq=None):
        """
        Parameters
        ----------
        prereq: str
          Prerequisites which need to be fulfilled (run without error) to consider
          benchmark worthwhile (ATM only during verification)
        """
        self.code = code
        self.setup = setup
        self.cleanup = cleanup or ''
        self.ncalls = ncalls
        self.repeat = repeat

        if name is None:
            try:
                name = _get_assigned_name(inspect.currentframe().f_back)
            except:
                pass

        self.name = name
        self.module_name = module_name

        self.description = description
        self.start_date = start_date
        self.logy = logy

        self.prereq = prereq

    def __repr__(self):
        return "Benchmark(%r, %r, name=%r)" % (self.code, self.setup, self.name)

    def __str__(self):
        return "Benchmark:%s" % self.name

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

    def run(self, ncalls=None, repeat=None):
        """
        Parameters
        ----------
        ncalls: int, optional
          If specified and non-0, would override specified in constructor ncalls
        repeat: int, optional
          If specified and non-0, would override specified in constructor repeat
        """
        ns = None
        try:
            stage = 'setup'
            ns = self._setup()

            if self.prereq:
                stage = 'prereq'
                exec self.prereq in ns

            stage = 'benchmark'
            result = magic_timeit(ns, self.code, ncalls=ncalls or self.ncalls,
                                  repeat=repeat or self.repeat, force_ms=True)
            result['succeeded'] = True
        except:
            buf = StringIO()
            traceback.print_exc(file=buf)
            result = {'succeeded': False,
                      'stage': stage,
                      'traceback': buf.getvalue()}

        if ns:
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

    def get_rst_label(self):
        """Return a sanitized label which can be used for rst referencing, figure files names etc
        """
        return re.sub('[][(),:\- ]', '_', self.name)

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

    def plot(self, db_path, branches=None, label='time', ax=None, title=True):
        import matplotlib.pyplot as plt
        from matplotlib.dates import MonthLocator, DateFormatter

        from vbench.db import BenchmarkDB
        db = BenchmarkDB.get_instance(db_path)
        results = self.get_results(db_path)

        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)
        if self.logy and branches is not None and len(branches):
            raise NotImplementedError("Plotting with logy and multiple branches is not yet supported")

        xlims = [] # xlimits to all plots to assure a full dates coverage
        # for older numpy we need to pre-digest results.revision so it
        # is sortable string type
        timing = [ 0 ] # just if there were no branches to plot
        results_revs = np.array(results.revision)
        if len(results_revs):
            results_revs = results_revs.astype('S%d' % len(results.revision[0]))
        for branch in (branches if branches is not None else [None]):
            # Select only the revisions belonging to the branch
            branch_revs = db.get_branch_revs(branch)
            results_ = results[np.in1d(results_revs, branch_revs)]
            if not len(results_):
                log.warning("Skipping plotting for branch %s since no revisions"
                            " were benchmarked for it" % branch)
                continue
            log.log(8, "Plotting for branch %s with %s revisions" % (branch, len(results_)))

            timing = results_['timing']
            if self.start_date is not None:
                timing = timing.truncate(before=self.start_date)

            label_ = "%s (%s)" % (branch, label) if branch is not None else label

            timing.plot(ax=ax, style='-', label=label_)
            xlims.append(ax.get_xlim())
            ax.set_xlabel('Date')
            ax.set_ylabel('milliseconds')

            if self.logy:
                ax2 = ax.twinx()
                try:
                    timing.plot(ax=ax2, label='%s (log scale)' % label,
                                style='r-',
                                logy=self.logy)
                    ax2.set_ylabel('milliseconds (log scale)')
                    ax.legend(loc='best')
                    ax2.legend(loc='best')
                except ValueError:
                    pass

        if branches is not None:
            ax.legend(loc='best')

        ylo, yhi = ax.get_ylim()

        # Start y axis from 0 if we are already close by
        # minimum range +- 10% of median of last couple entries
        # assures plots with little change look straight
        if ylo < 1 and yhi > 3:
            mid = np.median(timing[-100:])
            yhi = max(yhi, mid + mid * 0.30)
            ax.set_ylim([0, yhi])
        else:
            mid = np.median(timing[-100:])
            ylo = min(ylo, mid - mid * 0.15)
            yhi = max(yhi, mid + mid * 0.15)
            ax.set_ylim([ylo, yhi])

        formatter = DateFormatter("%b %Y")
        ax.xaxis.set_major_locator(MonthLocator())
        ax.xaxis.set_major_formatter(formatter)
        if len(xlims):
            ax.set_xlim((np.min(xlims, axis=0)[0], np.max(xlims, axis=0)[1]))
        ax.autoscale_view(scalex=True)

        if title:
            ax.set_title(self.name)

        return ax


def _get_assigned_name(frame):
    import ast

    # hackjob to retrieve assigned name for Benchmark
    info = inspect.getframeinfo(frame)
    line = info.code_context[0]
    path = info.filename
    lineno = info.lineno - 1

    def _has_assignment(line):
        try:
            mod = ast.parse(line.strip())
            return isinstance(mod.body[0], ast.Assign)
        except SyntaxError:
            return False

    if not _has_assignment(line):
        while not 'Benchmark' in line:
            prev = open(path).readlines()[lineno - 1]
            line = prev + line
            lineno -= 1

        if not _has_assignment(line):
            prev = open(path).readlines()[lineno - 1]
            line = prev + line
    varname = line.split('=', 1)[0].strip()
    return varname


def parse_stmt(frame):
    import ast
    info = inspect.getframeinfo(frame)
    call = info[-2][0]
    mod = ast.parse(call)
    body = mod.body[0]
    if isinstance(body, (ast.Assign, ast.Expr)):
        call = body.value
    elif isinstance(body, ast.Call):
        call = body
    return _parse_call(call)


def _parse_call(call):
    import ast
    func = _maybe_format_attribute(call.func)

    str_args = []
    for arg in call.args:
        if isinstance(arg, ast.Name):
            str_args.append(arg.id)
        elif isinstance(arg, ast.Call):
            formatted = _format_call(arg)
            str_args.append(formatted)

    return func, str_args, {}


def _format_call(call):
    func, args, kwds = _parse_call(call)
    content = ''
    if args:
        content += ', '.join(args)
    if kwds:
        fmt_kwds = ['%s=%s' % item for item in kwds.iteritems()]
        joined_kwds = ', '.join(fmt_kwds)
        if args:
            content = content + ', ' + joined_kwds
        else:
            content += joined_kwds
    return '%s(%s)' % (func, content)


def _maybe_format_attribute(name):
    import ast
    if isinstance(name, ast.Attribute):
        return _format_attribute(name)
    return name.id


def _format_attribute(attr):
    import ast
    obj = attr.value
    if isinstance(attr.value, ast.Attribute):
        obj = _format_attribute(attr.value)
    else:
        obj = obj.id
    return '.'.join((obj, attr.attr))


def indent(string, spaces=4):
    dent = ' ' * spaces
    return '\n'.join([dent + x for x in string.split('\n')])


class BenchmarkSuite(list):
    """Basically a list, but the special type is needed for discovery"""
    @property
    def benchmarks(self):
        """Discard non-benchmark elements of the list"""
        return filter(lambda elem: isinstance(elem, Benchmark), self)

# Modified from IPython project, http://ipython.org


def magic_timeit(ns, stmt, ncalls=None,
                 repeat=None, force_ms=False,
                 target_timing=0.1):
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

    timer = timeit.Timer(timer=timefunc)
    # this code has tight coupling to the inner workings of timeit.Timer,
    # but is there a better way to achieve that the code stmt has access
    # to the shell namespace?

    src = timeit.template % {'stmt': timeit.reindent(stmt, 8),
                             'setup': "pass"}
    # Track compilation time so it can be reported if too long
    # Minimum time above which compilation time will be reported
    try:
        code = compile(src, "<magic-timeit>", "exec")
    except:
        log.warning("Compilation of following code failed:\n%s" % src)
        raise

    try:
        exec code in ns
        timer.inner = ns["inner"]
    except:
        log.warning("Execution of following compiled code to obtain 'inner' has failed:\n%s" % src)
        raise
    #D import time; t0 = time.time()

    # if any of ncalls or repeat is unspecified -- deduce
    if ncalls is None or repeat is None:
        # determine number of iterations to get close to target timing
        number = ncalls or 1
        for _ in range(1, 200):
            timed = timer.timeit(number)
            if timed >= target_timing:
                break
            # estimate how much to step at once -- by looping and due to int() this estimate
            # should already be conservative enough to not "jump over".
            # This should allow to converge on target timing a bit faster
            # without wasting precious CPU cycles without doing any benchmarking.
            mult = 2**max(int(np.log2(target_timing/timed)), 1)
            #D print "%d timed at %.2g. multiplying by %.2g" % (number, timed, mult)
            number *= mult
            if timed * mult >= target_timing:
                # we already know that it should be close enough to
                # target timing
                break
        #D t1 = time.time()
        #D print "D: took %.2f seconds to figure out number %d" % (t1 - t0, number)
    else:
        #D t1 = time.time()
        number = ncalls

    # if it is still None
    if repeat is None and ncalls is None:
        # so number was deduced, thus take both repeat and
        # number to be equal to stay close to target timing
        # But have at least 3 repeats
        repeat = max(3, int(np.sqrt(number)))
        # and at least 1 run
        number = max(1, int(number // repeat))
    elif repeat is None:
        repeat = max(1, int(number // ncalls))
        number = ncalls
    elif ncalls is None:
        number = max(1, int(number // repeat))

    try:
        best = min(timer.repeat(repeat, number)) / number
    except:
        log.warning("Timing of following code has failed:\n%s" % src)
        raise

    if force_ms:
        order = 1
    else:
        if best > 0.0 and best < 1000.0:
            order = min(-int(math.floor(math.log10(best)) // 3), 3)
        elif best >= 1000.0:
            order = 0
        else:
            order = 3
    #D print "D: took %.2f seconds to repeat %d times with best=%.4g" % (time.time() - t1, repeat, best)
    return {'loops': number,
            'repeat': repeat,
            'timing': best * scaling[order],
            'units': units[order]}


def gather_benchmarks(ns):
    benchmarks = []
    for v in ns.values():
        if isinstance(v, Benchmark):
            benchmarks.append(v)
        elif isinstance(v, BenchmarkSuite):
            benchmarks.extend(v.benchmarks)
    return benchmarks

