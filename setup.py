#!/usr/bin/env python
from os import path
from setuptools import setup, find_packages

from ScrapyKeeper import __version__, __author__

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'requirements.txt')) as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]

setup(
    name='ScrapyKeeper',
    version=__version__,
    description='Admin ui for scrapy spider service',
    long_description=
    'Go to https://github.com/fliot/ScrapyKeeper/ for more information.',
    author=__author__,
    author_email='modongming91@gmail.com',
    maintainer="Francois Liot",
    maintainer_email="francois@liot.org",
    url='https://github.com/fliot/ScrapyKeeper/',
    license='MIT',
    include_package_data=True,
    packages=find_packages(),
    install_requires=install_requires,

    entry_points={
        'console_scripts': {
            'scrapykeeper = ScrapyKeeper.run:main'
        },
    },

    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
    ],
)
