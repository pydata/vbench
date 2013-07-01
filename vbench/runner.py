import cPickle as pickle
import os
import subprocess

from vbench.git import GitRepo, BenchRepo
from vbench.db import BenchmarkDB
from vbench.utils import multires_order

from datetime import datetime

import logging
log = logging.getLogger('vb.runner')

_RUN_ORDERS = dict(
    normal=lambda x:x,
    reverse=lambda x:x[::-1],
    multires=multires_order,
    )

class BenchmarkRunner(object):
    """

    Parameters
    ----------
    benchmarks : list of Benchmark objects
    repo_path
    build_cmd
    db_path
    run_option : {'eod', 'all', 'last', integer}, default: 'eod'
        eod: use the last revision for each calendar day
        all: benchmark every revision
        last: only try to run the last revision
        some integer N: run each N revisions
    run_order :
        normal : original order (default)
        reverse: in reverse order (latest first)
        multires: cover all revisions but in the order increasing
                  temporal detail
    overwrite : boolean
    dependencies : list or None
        should be list of modules visible in cwd
    """

    def __init__(self, benchmarks, repo_path, repo_url,
                 build_cmd, db_path, tmp_dir,
                 prep_cmd,
                 clean_cmd=None,
                 run_option='eod', run_order='normal',
                 start_date=None, overwrite=False,
                 module_dependencies=None,
                 always_clean=False,
                 use_blacklist=True):
        log.info("Initializing benchmark runner for %d benchmarks" % (len(benchmarks)))
        self._benchmarks = None
        self._checksums = None

        self.start_date = start_date
        self.run_option = run_option
        self.run_order = run_order

        self.repo_path = repo_path
        self.db_path = db_path

        self.repo = GitRepo(self.repo_path)
        self.db = BenchmarkDB(db_path)

        self.use_blacklist = use_blacklist

        self.blacklist = set(self.db.get_rev_blacklist())

        # where to copy the repo
        self.tmp_dir = tmp_dir
        self.bench_repo = BenchRepo(repo_url, self.tmp_dir, build_cmd,
                                    prep_cmd,
                                    clean_cmd,
                                    always_clean=always_clean,
                                    dependencies=module_dependencies)

        self.benchmarks = benchmarks

    def _get_benchmarks(self):
        return self._benchmarks

    def _set_benchmarks(self, benchmarks):
        self._benchmarks = benchmarks
        self._checksums = [b.checksum for b in benchmarks]
        self._register_benchmarks()

    benchmarks = property(fget=_get_benchmarks, fset=_set_benchmarks)
    checksums = property(fget=lambda self:self._checksums)

    def run(self):
        log.info("Collecting revisions to run")
        revisions = self._get_revisions_to_run()
        ran_revisions = []
        log.info("Running benchmarks for %d revisions" % (len(revisions),))
        for rev in revisions:
            if self.use_blacklist and rev in self.blacklist:
                log.warn('Skipping blacklisted %s' % rev)
                continue

            any_succeeded, n_active = self._run_and_write_results(rev)
            ran_revisions.append((rev, (any_succeeded, n_active)))
            log.debug("%s succeeded among %d active benchmarks",
                      {True: "Some", False: "None"}[any_succeeded],
                      n_active)
            if not any_succeeded and n_active > 0:
                self.bench_repo.hard_clean()

                any_succeeded2, n_active = self._run_and_write_results(rev)

                # just guessing that this revision is broken, should stop
                # wasting our time
                if (not any_succeeded2 and n_active > 5
                    and self.use_blacklist):
                    log.warn('Blacklisting %s' % rev)
                    self.db.add_rev_blacklist(rev)
        return ran_revisions

    def _run_and_write_results(self, rev):
        """
        Returns True if any runs succeeded
        """
        n_active_benchmarks, results = self._run_revision(rev)
        tracebacks = []

        any_succeeded = False

        for checksum, timing in results.iteritems():
            if 'traceback' in timing:
                tracebacks.append(timing['traceback'])

            timestamp = self.repo.timestamps[rev]

            any_succeeded = any_succeeded or 'timing' in timing

            self.db.write_result(checksum, rev, timestamp,
                                 timing.get('loops'),
                                 timing.get('timing'),
                                 timing.get('traceback'))

        return any_succeeded, n_active_benchmarks

    def _register_benchmarks(self):
        log.info('Getting benchmarks')
        ex_benchmarks = self.db.get_benchmarks()
        db_checksums = set(ex_benchmarks.index)
        log.info("Registering %d benchmarks" % len(ex_benchmarks))
        for bm in self.benchmarks:
            if bm.checksum in db_checksums:
                self.db.update_name(bm)
            else:
                log.info('Writing new benchmark %s, %s' % (bm.name, bm.checksum))
                self.db.write_benchmark(bm)

    def _run_revision(self, rev):
        need_to_run = self._get_benchmarks_for_rev(rev)

        if not need_to_run:
            log.info('No benchmarks need running at %s' % rev)
            return 0, {}

        log.info('Running %d benchmarks for revision %s' % (len(need_to_run), rev))
        for bm in need_to_run:
            log.debug(bm.name)

        self.bench_repo.switch_to_revision(rev)

        pickle_path = os.path.join(self.tmp_dir, 'benchmarks.pickle')
        results_path = os.path.join(self.tmp_dir, 'results.pickle')
        if os.path.exists(results_path):
            os.remove(results_path)
        pickle.dump(need_to_run, open(pickle_path, 'w'))

        # run the process
        cmd = 'python vb_run_benchmarks.py %s %s' % (pickle_path, results_path)
        log.debug("CMD: %s" % cmd)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True,
                                cwd=self.tmp_dir)
        stdout, stderr = proc.communicate()

        if stdout:
            log.debug('stdout: %s' % stdout)

        if proc.returncode:
            log.warn("Returned with non-0 code: %d" % proc.returncode)

        if stderr:
            log.warn("stderr: %s" % stderr)
            if ("object has no attribute" in stderr or
                'ImportError' in stderr):
                log.warn('HARD CLEANING!')
                self.bench_repo.hard_clean()

        if not os.path.exists(results_path):
            log.warn('Failed for revision %s' % rev)
            return len(need_to_run), {}

        results = pickle.load(open(results_path, 'r'))

        try:
            os.remove(pickle_path)
        except OSError:
            pass

        return len(need_to_run), results

    def _get_benchmarks_for_rev(self, rev):
        existing_results = self.db.get_rev_results(rev)
        need_to_run = []

        timestamp = self.repo.timestamps[rev]

        for b in self.benchmarks:
            if b.start_date is not None and b.start_date > timestamp:
                continue

            if b.checksum not in existing_results:
                need_to_run.append(b)

        return need_to_run

    def _get_revisions_to_run(self):

        # TODO generalize someday to other vcs...git only for now

        rev_by_timestamp = self.repo.shas.sort_index()

        # # assume they're in order, but check for now
        # assert(rev_by_timestamp.index.is_monotonic)

        if self.start_date is not None:
            rev_by_timestamp = rev_by_timestamp.ix[self.start_date:]

        if self.run_option == 'eod':
            grouped = rev_by_timestamp.groupby(datetime.date)
            revs_to_run = grouped.apply(lambda x: x[-1]).values
        elif self.run_option == 'all':
            revs_to_run = rev_by_timestamp.values
        elif self.run_option == 'last':
            revs_to_run = rev_by_timestamp.values[-1:]
            # TODO: if the very last revision fails, there should be a way
            # to look for the second last, etc, until the last one that was run
        elif isinstance(self.run_option, int):
            revs_to_run = rev_by_timestamp.values[::self.run_option]
        else:
            raise ValueError('unrecognized run_option=%r' % self.run_option)

        if not self.run_order in _RUN_ORDERS:
            raise ValueError('unrecognized run_order=%r. Must be among %s'
                             % (self.run_order, _RUN_ORDERS.keys()))
        revs_to_run = _RUN_ORDERS[self.run_order](revs_to_run)

        return revs_to_run
