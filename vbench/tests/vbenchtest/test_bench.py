#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:

__author__ = 'Yaroslav Halchenko'
__copyright__ = 'Copyright (c) 2013 Yaroslav Halchenko'
__license__ = 'MIT'

import os
import shutil

from glob import glob
from os.path import exists, join as pjoin, dirname, basename

import numpy as np
from nose.tools import ok_, eq_
from numpy.testing import assert_array_equal

from vbench.api import BenchmarkRunner

#import logging
#log = logging.getLogger('vb')
#log.setLevel('DEBUG')


def test_benchmarkrunner():
    from suite import *

    # Just to make sure there are no left-overs
    shutil.rmtree(TMP_DIR)
    if exists(DB_PATH):
        os.unlink(DB_PATH)
    ok_(not exists(DB_PATH), "%s should not yet exist" % TMP_DIR)

    runner = BenchmarkRunner(benchmarks, REPO_PATH, REPO_URL,
                             BUILD, DB_PATH, TMP_DIR, PREPARE,
                             branches=BRANCHES,
                             clean_cmd=CLEAN,
                             run_option='all', run_order='normal',
                             start_date=START_DATE,
                             module_dependencies=DEPENDENCIES)
    revisions_to_run = runner._get_revisions_to_run()
    eq_(len(revisions_to_run), 7, "we should have only this many revisions")
    revisions_ran = runner.run()
    # print "D1: ", revisions_ran
    # for this test we should inject our "failed to build revision"
    # Since no tests were ran for it -- it is not reported
    revisions_ran_ = [x[0] for x in revisions_ran]
    revisions_ran_.insert(4, 'e83ffa5')
    assert_array_equal(revisions_ran_, revisions_to_run,
       "All revisions should have been ran")

    # First revision
    eq_(revisions_ran[0][1], (False, 3))    # no functions were available at that point
    eq_(revisions_ran[1][1], (True, 3))     # all 3 tests were available in the first rev

    ok_(exists(TMP_DIR))
    ok_(exists(DB_PATH))

    eq_(runner.blacklist, set(['e83ffa5']))   # one which failed to build

    # Run 2nd time and verify that all are still listed BUT none new succeeds
    revisions_ran = runner.run()
    #print "D2: ", revisions_ran
    for rev, v in revisions_ran:
        eq_(v, (False, 0))

    # What if we expand list of benchmarks and run 3rd time
    runner.benchmarks = collect_benchmarks(['vb_sins', 'vb_sins2'])
    revisions_ran = runner.run()
    # for that single added benchmark there still were no function
    eq_(revisions_ran[0][1], (False, 1))
    # all others should have "succeeded" on that single one
    for rev, v in revisions_ran[1:]:
        eq_(v, (True, 1))

    # and on 4th run -- nothing new
    revisions_ran = runner.run()
    for rev, v in revisions_ran:
        eq_(v, (False, 0))

    eq_(set(runner.db.get_branches()), set(['origin/branch1', 'master']))
    # check that 'ecf481d' is marked present in both branches
    # in DB:
    eq_(set(runner.db.get_branch_revs('origin/branch1')), set(['d22c3e7', 'ecf481d']))
    ok_('ecf481d' in runner.db.get_branch_revs('master'))

    # in the GitRepo
    eq_(set(runner.repo.sha_branches['ecf481d']), set(['master', 'origin/branch1']))

    # Let's rerun the runner instructing to run already known results
    # aiming for new 'min's
    old_results = [runner.db.get_benchmark_results(b.checksum) for b in benchmarks]
    runner.existing = 'min'
    revisions_ran = runner.run()
    eq_(revisions_ran[0], ('e9375c8', (False, 0)))   # still has nothing
    # all others should have got all benchmarks re-ran
    for rev, v in revisions_ran[1:]:
        eq_(v, (True, len(runner.benchmarks)))
    # and new results should be only better
    new_results = [runner.db.get_benchmark_results(b.checksum) for b in benchmarks]
    for o, n in zip(old_results, new_results):
        # we can't test if it got better actually, but we can assure
        # that it got no worse
        ok_(np.all(o.timing[1:] - n.timing[1:] >= 0))

    # Now let's smoke test generation of the .rst files
    from vbench.reports import generate_rst_files
    rstdir = pjoin(TMP_DIR, 'sources')
    # work in both modes -- agglomerate and per branch
    for branches in (None, BRANCHES):
        generate_rst_files(runner.benchmarks, DB_PATH, rstdir,
                           description="""VERY LONG DESCRIPTION""", branches=branches)

        # Verify that it all looks close to the desired
        image_files = [basename(x) for x in glob(pjoin(rstdir, 'vbench/figures/*.png'))]
        target_image_files = [b.get_rst_label() + '.png' for b in runner.benchmarks]
        eq_(set(image_files), set(target_image_files))

        rst_files = [basename(x) for x in glob(pjoin(rstdir, 'vbench/*.rst'))]
        target_rst_files = [b.name + '.rst' for b in runner.benchmarks]
        eq_(set(rst_files), set(target_rst_files))

        module_files = [basename(x) for x in glob(pjoin(rstdir, '*.rst'))]
        target_module_files = list(set(['vb_' + b.module_name + '.rst' for b in runner.benchmarks]))
        eq_(set(module_files), set(target_module_files + ['index.rst']))

    #print TMP_DIR, DB_PATH, rstdir
    shutil.rmtree(TMP_DIR)
    shutil.rmtree(dirname(DB_PATH))
