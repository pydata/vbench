import sys
import cPickle as pickle
import time

import logging
try:
    from vbench.log import log
except ImportError:
    # if no pandas -- just a silent one
    log = logging.getLogger('vb')
    log.setLevel(logging.INFO)

if len(sys.argv) != 3:
    print('Usage: script.py input output')
    sys.exit()

in_path, out_path = sys.argv[1:]
benchmarks = pickle.load(open(in_path))

results = {}
errors = 0
for bmk in benchmarks:
    t0 = time.time()
    try:
        res = bmk.run()
        log.debug("Benchmark %s completed in %.2s sec" % (bmk, time.time()-t0))
    except Exception, e:
        errors += 1
        log.error("E: Got an exception while running %s\n%s" % (bmk, e))
        continue

    results[bmk.checksum] = res

    if not res['succeeded']:
        errors += 1
        log.warning("I: Failed to succeed with %s in stage %s."
                    % (bmk, res.get('stage', 'UNKNOWN')))
        log.info(res.get('traceback', 'Traceback: UNKNOWN'))

benchmarks = pickle.dump(results, open(out_path, 'w'))
sys.exit(errors)
