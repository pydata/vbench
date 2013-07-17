#emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*- 
#ex: set sts=4 ts=4 sw=4 noet:
"""Functionality to ease generation of vbench reports
"""
__copyright__ = '2013 Yaroslav Halchenko'
__license__ = 'MIT'

import os

import pandas, numpy as np
import scipy.stats as ss

import logging
log = logging.getLogger('vb.reports')

#
# Some checks to decide either there was a regression.  ATM there is
# only a single simple check
#
class ConsistentlyWorse(object):
    """Basic check to detect regression if last n commits are worse than continuous n best commits
    """

    def __init__(self, ncommits=10, thr=0.01, Tpthr=0.001):
        self.ncommits = ncommits
        self.thr = thr
        self.Tpthr = Tpthr

    def __str__(self):
        return "ConsistentlyWorse(%d)" % (self.ncommits,)
        # since noone would care about gory details anyways
        #return "ConsistentlyWorse(%d, %.2g, %.2g)" \
        #  % (self.ncommits, self.thr, self.Tpthr)

    def __call__(self, results):
        """
        Returns
        -------
        {'reference' : series,
         'reference_timing': float,
         'target' : series,
         'target_timing': float,
         'slowdown_percent' : float,
         'latest_better': series,
         'earliest_notworse': series,
         'statistic' : float,
         }
        """
        ncommits = self.ncommits
        Tpthr = self.Tpthr

        means = pandas.rolling_mean(results.timing, 10)
        assert(len(means) == len(results))

        idxs = np.isfinite(means)
        results = results[idxs]
        means = means[idxs]

        min_idx = np.argmin(means)
        min_ = means[min_idx]

        # samples which
        reference_samples = results[
            max(0, min_idx - ncommits//2):
            min(min_idx + ncommits//2, len(results))]
        assert(len(reference_samples) <= ncommits)

        test_samples = results[-min(ncommits, len(means)):]

        F, Fp = ss.f_oneway(reference_samples.timing, test_samples.timing)

        if Fp > self.thr:                  # non-significant?
            return None

        # let's try to deduce which one was the first offending commit
        # So run t-test on every timing against test_samples timing
        Tts, Tps = ss.ttest_1samp(test_samples.timing, results.timing)
        assert( len(Tts) == len(results) ) # for paranoid yoh

        better = np.logical_and(Tts < 0, Tps <= Tpthr)
        better_idx = np.where(better)[0]
        # exclude the target ones
        better_idx = better_idx[better_idx < len(results)-ncommits]

        if len(better_idx):
            latest_better_i = better_idx[-1]
            latest_better = results.ix[latest_better_i]
            earliest_notworse = results.ix[latest_better_i+1]
        else:
            latest_better = earliest_notworse = None

        return {'reference' : results.ix[min_idx],
                'reference_timing': means.ix[min_idx],
                'target' : results.ix[-1],
                'target_timing': means.ix[-1],
                'slowdown_percent' : 100.*(results.timing[-1] - means.ix[min_idx])/means.ix[min_idx],
                'latest_better': latest_better,
                'earliest_notworse': earliest_notworse,
                'statistic' : Fp,
            }

