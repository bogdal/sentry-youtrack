# ~*~ coding: utf-8 ~*~
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
from sentry_youtrack import VERSION
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_settings')


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]
    test_args = []

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='sentry-youtrack',
    version=VERSION,
    author='Adam Bogdał',
    author_email='adam@bogdal.pl',
    url='http://github.com/bogdal/sentry-youtrack',
    description='A Sentry extension which integrates with YouTrack',
    long_description=open('README.rst').read(),
    license='BSD',
    packages=find_packages(),
    install_requires=[
        'beautifulsoup4>=4.5.1',
        'sentry>=8.0.0',
        'unidecode>=0.4.19'
    ],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'sentry.apps': [
            'sentry_youtrack = sentry_youtrack',
        ],
        'sentry.plugins': [
            'sentry_youtrack = sentry_youtrack.plugin:YouTrackPlugin'
        ],
    },
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Topic :: Software Development',
        'Programming Language :: Python',
        'License :: OSI Approved :: BSD License',
    ],
    cmdclass={
        'test': PyTest
    },
    tests_require=[
        'pytest',
        'vcrpy>=1.7.3',
    ]
)
