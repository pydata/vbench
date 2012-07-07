import unittest

# from gitbench.db import BenchmarkDB  # FIXME: test is actually empty


class TestBenchmarkDB(unittest.TestCase):

    test_path = '__test__.db'

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vvs', '-x', '--pdb', '--pdb-failure'],
                   exit=False)
