import sys
import cPickle as pickle

if len(sys.argv) != 3:
    print('Usage: script.py input output')
    sys.exit()

in_path, out_path = sys.argv[1:]
benchmarks = pickle.load(open(in_path))

results = {}
errors = 0
for bmk in benchmarks:
    try:
        res = bmk.run()
    except Exception, e:
        errors += 1
        print("E: Got an exception while running %s\n%s" % (bmk, e))
        continue

    results[bmk.checksum] = res

    if not res['succeeded']:
        errors += 1
        print("I: Failed to succeed with %s in stage %s."
               % (bmk, res.get('stage', 'UNKNOWN')))
        print(res.get('traceback', 'Traceback: UNKNOWN'))

benchmarks = pickle.dump(results, open(out_path, 'w'))
sys.exit(errors)
