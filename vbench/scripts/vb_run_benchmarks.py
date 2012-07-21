import sys
import traceback
import cPickle as pickle

if len(sys.argv) != 3:
    print 'Usage: script.py input output'
    sys.exit()

in_path, out_path = sys.argv[1:]
benchmarks = pickle.load(open(in_path))

results = {}
for bmk in benchmarks:
    try:
        res = bmk.run()
        results[bmk.checksum] = res
    except Exception:
        print >> sys.stderr, 'Exception in benchmark %s:' % bmk.name
        traceback.print_exc()
        continue

benchmarks = pickle.dump(results, open(out_path, 'w'))
