#!/usr/bin/env python
from setuptools import setup, find_packages
from sentry_youtrack import VERSION

install_requires = [
    'sentry>=5.1.0',
    'requests>=1.1.0',
    'BeautifulSoup>=3.2.1',
]

setup(
    name='sentry-youtrack',
    version=VERSION,
    author='Adam Bogdal',
    author_email='adam@bogdal.pl',
    url='http://github.com/bogdal/sentry-youtrack',
    description='A Sentry extension which integrates with YouTrack',
    long_description=open('README.rst').read(),
    license='BSD',
    packages=find_packages(),
    install_requires=install_requires,
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
)
