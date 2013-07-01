#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
"""Functionality to ease generation of vbench reports
"""
__copyright__ = '2012-2013 Wes McKinney, Yaroslav Halchenko'
__license__ = 'MIT'

import os

import logging
log = logging.getLogger('vb.reports')

def generate_rst_files(benchmarks, dbpath, outpath, description=""):
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

        fig_full_path = os.path.join(fig_base_path, '%s.png' % bmk.name)

        # make the figure
        plt.figure(figsize=(10, 6))
        ax = plt.gca()
        bmk.plot(dbpath, ax=ax)

        start, end = ax.get_xlim()

        plt.xlim([start - 30, end + 30])
        plt.savefig(fig_full_path, bbox_inches='tight')
        plt.close('all')

        fig_rel_path = 'vbench/figures/%s.png' % bmk.name
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
        benchmarks_by_module = {}
        for b in benchmarks:
            module_name = b.module_name or "orphan"
            if not module_name in benchmarks_by_module:
                benchmarks_by_module[module_name] = []
            benchmarks_by_module[module_name].append(b)

        for modname, mod_bmks in sorted(benchmarks_by_module.items()):
            print >> f, '    vb_%s' % modname
            modpath = os.path.join(outpath, 'vb_%s.rst' % modname)
            with open(modpath, 'w') as mh:
                header = '%s\n%s\n\n' % (modname, '=' * len(modname))
                print >> mh, header

                for bmk in mod_bmks:
                    print >> mh, bmk.name
                    print >> mh, '-' * len(bmk.name)
                    print >> mh, '.. include:: vbench/%s.rst\n' % bmk.name

