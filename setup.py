#/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

DESCRIPTION = "Performance benchmarking and monitoring tool"
LONG_DESCRIPTION = """
Performance benchmarking and monitoring tool
"""

REQUIRES = ['sqlalchemy', 'pandas']
DISTNAME = 'vbench'
LICENSE = 'BSD'
AUTHOR = "Wes McKinney"
AUTHOR_EMAIL = "wesmckinn@gmail.com"
URL = "https://github.com/wesm/vbench"
CLASSIFIERS = [
    'Development Status :: 2 - Pre-Alpha',
    'Environment :: Console',
    'Operating System :: OS Independent',
    'Intended Audience :: Science/Research',
    'Programming Language :: Python',
    'Topic :: Scientific/Engineering',
]

MAJOR = 0
MINOR = 1
ISRELEASED = False
VERSION = '%d.%d' % (MAJOR, MINOR)

FULLVERSION = VERSION
if not ISRELEASED:
    FULLVERSION += '.beta'

if __name__ == '__main__':
    setup(name=DISTNAME,
          version=VERSION,
          author=AUTHOR,
          author_email=AUTHOR_EMAIL,
          packages=['vbench', 'vbench.tests'],
          package_data={'vbench' : ['scripts/*.py']},
          description=DESCRIPTION,
          license=LICENSE,
          url=URL,
          long_description=LONG_DESCRIPTION,
          classifiers=CLASSIFIERS,
          platforms='any')
