import cPickle as pickle
import os
import subprocess

from vbench.git import GitRepo, BenchRepo
from vbench.db import BenchmarkDB

from datetime import datetime


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
    overwrite : boolean
    dependencies : list or None
        should be list of modules visible in cwd
    time : boolean
        whether to measure how much running the benchmarks takes
    """

    def __init__(self, benchmarks, repo_path, repo_url,
                 build_cmd, db_path, tmp_dir,
                 preparation_cmd,
                 run_option='eod', start_date=None, overwrite=False,
                 module_dependencies=None,
                 always_clean=False,
                 use_blacklist=True,
                 time=True):

        self.benchmarks = benchmarks
        self.checksums = [b.checksum for b in benchmarks]

        self.start_date = start_date
        self.run_option = run_option

        self.repo_path = repo_path
        self.db_path = db_path

        self.repo = GitRepo(self.repo_path)
        self.db = BenchmarkDB(db_path)

        self.use_blacklist = use_blacklist

        self.blacklist = set(self.db.get_rev_blacklist())
        self.time = time
        # where to copy the repo
        self.tmp_dir = tmp_dir
        self.bench_repo = BenchRepo(repo_url, self.tmp_dir, build_cmd,
                                    preparation_cmd,
                                    always_clean=always_clean,
                                    dependencies=module_dependencies)
        self._register_benchmarks()
        self._python = os.environ.get('VBENCH_PYTHON', 'python')

    def run(self):
        revisions = self._get_revisions_to_run()

        for rev in revisions:
            if self.use_blacklist and rev in self.blacklist:
                print 'SKIPPING BLACKLISTED %s' % rev
                continue

            any_succeeded, n_active = self._run_and_write_results(rev)
            if not any_succeeded and n_active > 0:
                self.bench_repo.hard_clean()

                any_succeeded2, n_active = self._run_and_write_results(rev)

                # just guessing that this revision is broken, should stop
                # wasting our time
                if (not any_succeeded2 and n_active > 5
                    and self.use_blacklist):
                    print 'BLACKLISTING %s' % rev
                    self.db.add_rev_blacklist(rev)

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
        ex_benchmarks = self.db.get_benchmarks()
        db_checksums = set(ex_benchmarks.index)
        for bm in self.benchmarks:
            if bm.checksum in db_checksums:
                self.db.update_name(bm)
            else:
                print 'Writing new benchmark %s, %s' % (bm.name, bm.checksum)
                self.db.write_benchmark(bm)

    def _run_revision(self, rev):
        need_to_run = self._get_benchmarks_for_rev(rev)

        if not need_to_run:
            print 'No benchmarks need running at %s' % rev
            return 0, {}

        print 'Running %d benchmarks for revision %s' % (len(need_to_run), rev)
        for bm in need_to_run:
            print bm.name

        self.bench_repo.switch_to_revision(rev)

        pickle_path = os.path.join(self.tmp_dir, 'benchmarks.pickle')
        results_path = os.path.join(self.tmp_dir, 'results.pickle')
        if os.path.exists(results_path):
            os.remove(results_path)
        pickle.dump(need_to_run, open(pickle_path, 'w'))

        # run the process
        cmd = '%s vb_run_benchmarks.py %s %s' % (self._python, pickle_path,
                                                 results_path)
        if self.time:
            cmd = 'time ' + cmd
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                shell=True,
                                cwd=self.tmp_dir)
        stdout, stderr = proc.communicate()

        print 'stdout: %s' % stdout

        if stderr:
            if ("object has no attribute" in stderr or
                'ImportError' in stderr):
                print stderr
                print 'HARD CLEANING!'
                self.bench_repo.hard_clean()
            print stderr

        if not os.path.exists(results_path):
            print 'Failed for revision %s' % rev
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
            raise Exception('unrecognized run_option %s' % self.run_option)

        return revs_to_run
