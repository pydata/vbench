#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:

__author__ = 'Yaroslav Halchenko'
__copyright__ = 'Copyright (c) 2013 Yaroslav Halchenko'
__license__ = 'MIT'

import os
import shutil

from glob import glob
from os.path import exists, join as pjoin, dirname, basename

from nose.tools import ok_, eq_
from numpy.testing import assert_array_equal

#import logging
#log = logging.getLogger('vb')
#log.setLevel('DEBUG')


def test_benchmarkrunner():
    from vbench.api import BenchmarkRunner
    from suite import *

    # Just to make sure there are no left-overs
    shutil.rmtree(TMP_DIR)
    if exists(DB_PATH):
        os.unlink(DB_PATH)
    ok_(not exists(DB_PATH))

    runner = BenchmarkRunner(benchmarks, REPO_PATH, REPO_URL,
                             BUILD, DB_PATH, TMP_DIR, PREPARE,
                             clean_cmd=CLEAN,
                             run_option='all', run_order='normal',
                             start_date=START_DATE,
                             module_dependencies=DEPENDENCIES)
    revisions_to_run = runner._get_revisions_to_run()
    eq_(len(revisions_to_run), 4)                # we had 4 so far

    revisions_ran = runner.run()
    # print "D1: ", revisions_ran
    assert_array_equal([x[0] for x in revisions_ran],
                       revisions_to_run)
    # First revision
    eq_(revisions_ran[0][1], (False, 3))    # no functions were available at that point
    eq_(revisions_ran[1][1], (True, 3))     # all 3 tests were available in the first rev

    ok_(exists(TMP_DIR))
    ok_(exists(DB_PATH))

    eq_(len(runner.blacklist), 0)

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

    # Now let's smoke test generation of the .rst files
    from vbench.reports import generate_rst_files
    rstdir = pjoin(TMP_DIR, 'sources')
    generate_rst_files(runner.benchmarks, DB_PATH, rstdir, """VERY LONG DESCRIPTION""")

    # Verify that it all looks close to the desired
    image_files = [basename(x) for x in glob(pjoin(rstdir, 'vbench/figures/*.png'))]
    target_image_files = [b.name + '.png' for b in runner.benchmarks]
    eq_(set(image_files), set(target_image_files))

    rst_files = [basename(x) for x in glob(pjoin(rstdir, 'vbench/*.rst'))]
    target_rst_files = [b.name + '.rst' for b in runner.benchmarks]
    eq_(set(rst_files), set(target_rst_files))

    module_files = [basename(x) for x in glob(pjoin(rstdir, '*.rst'))]
    target_module_files = list(set(['vb_' + b.module_name + '.rst' for b in runner.benchmarks]))
    eq_(set(module_files), set(target_module_files + ['index.rst']))

    #print TMP_DIR
    shutil.rmtree(TMP_DIR)
    shutil.rmtree(dirname(DB_PATH))
