import os
from datetime import datetime

from vbench.api import collect_benchmarks

benchmarks = collect_benchmarks(
    ['vb_sins'])

cur_dir = os.path.dirname(__file__)
REPO_PATH = os.path.join(cur_dir, 'vbenchtest')
REPO_URL = 'git://github.com/yarikoptic/vbenchtest.git'
DB_PATH = os.path.join(cur_dir, 'db/benchmarks.db')
TMP_DIR = os.path.join(cur_dir, 'tmp')
# Assure corresponding directories existence
for s in (REPO_PATH, os.path.dirname(DB_PATH), TMP_DIR):
    if not os.path.exists(s):
        os.makedirs(s)

PREPARE = """
python setup.py clean
"""

CLEAN=PREPARE

BUILD = """
python setup.py build_ext --inplace
"""

DEPENDENCIES = [os.path.join(cur_dir, 'vb_common.py')]

START_DATE = datetime(2011, 01, 01)
