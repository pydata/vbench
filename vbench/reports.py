#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
"""Functionality to ease generation of vbench reports
"""
__copyright__ = '2012-2013 Wes McKinney, Yaroslav Halchenko'
__license__ = 'MIT'

import os

from .analysis import ConsistentlyWorse

import logging
log = logging.getLogger('vb.reports')

def group_benchmarks_by_module(benchmarks):
    benchmarks_by_module = {}
    for b in benchmarks:
        module_name = b.module_name or "orphan"
        if not module_name in benchmarks_by_module:
            benchmarks_by_module[module_name] = []
        benchmarks_by_module[module_name].append(b)
    return benchmarks_by_module

def generate_rst_files(benchmarks, dbpath, outpath, branches=None, description=""):
    import matplotlib as mpl
    mpl.use('Agg')
    import matplotlib.pyplot as plt

    vb_path = os.path.join(outpath, 'vbench')
    fig_base_path = os.path.join(vb_path, 'figures')

    if not os.path.exists(vb_path):
        log.info('Creating %s' % vb_path)
        os.makedirs(vb_path)

    if not os.path.exists(fig_base_path):
        log.info('Creating %s' % fig_base_path)
        os.makedirs(fig_base_path)

    log.info("Generating rst files for %d benchmarks" % (len(benchmarks)))
    for bmk in benchmarks:
        log.debug('Generating rst file for %s' % bmk.name)
        rst_path = os.path.join(outpath, 'vbench/%s.rst' % bmk.name)

        fig_full_path = os.path.join(fig_base_path, '%s.png' % bmk.get_rst_label())

        # make the figure
        plt.figure(figsize=(10, 6))
        ax = plt.gca()
        bmk.plot(dbpath, branches=branches, ax=ax)

        start, end = ax.get_xlim()

        plt.xlim([start - 30, end + 30])
        plt.savefig(fig_full_path, bbox_inches='tight')
        plt.close('all')

        fig_rel_path = 'vbench/figures/%s.png' % bmk.get_rst_label()
        rst_text = bmk.to_rst(image_path=fig_rel_path)
        with open(rst_path, 'w') as f:
            f.write(rst_text)

    with open(os.path.join(outpath, 'index.rst'), 'w') as f:
        print >> f, """
Performance Benchmarks
======================

These historical benchmark graphs were produced with `vbench
<http://github.com/pydata/vbench>`__.

%(description)s

.. toctree::
    :hidden:
    :maxdepth: 3
""" % locals()
        # group benchmarks by module there belonged to
        benchmarks_by_module = group_benchmarks_by_module(benchmarks)

        for modname, mod_bmks in sorted(benchmarks_by_module.items()):
            print >> f, '    vb_%s' % modname
            modpath = os.path.join(outpath, 'vb_%s.rst' % modname)
            with open(modpath, 'w') as mh:
                header = '%s\n%s\n\n' % (modname, '=' * len(modname))
                print >> mh, header

                for bmk in mod_bmks:
                    print >> mh, ".. _%s:\n" % bmk.get_rst_label()
                    print >> mh, bmk.name
                    print >> mh, '-' * len(bmk.name)
                    print >> mh, '.. include:: vbench/%s.rst\n' % bmk.name


def generate_rst_analysis(benchmarks, dbpath, outpath, gh_repo=None,
                          checks=[ConsistentlyWorse(10, 0.01)]):
    """Provides basic analysis of benchmarks and generates a report listing the offenders
    """
    with open(os.path.join(outpath, 'analysis.rst'), 'w') as f:
        print >> f, """
Benchmarks Performance Analysis
===============================
"""
        all_res = []
        for b in benchmarks:
            # basic analysis: find
            for check in checks:
                results = b.get_results(dbpath)
                res = check(results)
                if res:
                    res['benchmark'] = ":ref:`%s`" % b.get_rst_label()
                    res['reference_date'] = res['reference'].name.strftime("%Y.%m.%d")
                    res['check'] = str(check)
                    if res['latest_better'] is not None and res['earliest_notworse'] is not None:
                        r1 = res['latest_better']['revision']
                        r2 = res['earliest_notworse']['revision']
                        # how many commits are in between
                        ndiff = len(results[res['latest_better'].name:
                                            res['earliest_notworse'].name])-1
                        diff = '%(r1)s...%(r2)s' % locals()
                        diff_ = '(>=%(ndiff)d)%(diff)s' % locals() if ndiff > 1 else diff
                        res['source_diff'] = \
                            ('`%(diff_)s <%(gh_repo)s/compare/%(diff)s>`__'
                             if gh_repo else "%(diff_)s" ) % locals()
                    else:
                         res['source_diff'] = 'N/A'
                    all_res.append(res)

        if res:
            # sort all by the slowdown_percent showing the slowest first
            all_res = sorted(all_res, key=lambda x:x['slowdown_percent'], reverse=True)
            print >> f, """
.. container:: benchmarks_analysis clear

  .. list-table::
     :header-rows: 1
     :stub-columns: 1
     :widths: 32 30 6 4 4 4 20

     * - Benchmark
       - Check
       - Slowdown %
       - Reference date
       - Reference timing
       - Target timing
       - Possible recent"""

            for res in all_res:
                print >> f, """\
     * - %(benchmark)s
       - %(check)s
       - %(slowdown_percent).1f
       - %(reference_date)s
       - %(reference_timing).2g
       - %(target_timing).2g
       - %(source_diff)s""" % res
