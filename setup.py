#!/usr/bin/python3

import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    url='https://github.com/qtc-de/tricot',
    name='tricot',
    author='Tobias Neitzel (@qtc_de)',
    version='1.10.1',
    author_email='',

    description='Trivial Command Testser',
    long_description=long_description,
    long_description_content_type='text/markdown',

    packages=['tricot'],
    install_requires=[
                        'PyYAML',
                        'termcolor',
                        'docker',
                     ],
    scripts=[
                'bin/tricot',
            ],
    classifiers=[
                    'Programming Language :: Python :: 3',
                    'Operating System :: Unix',
                    'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                ],
)
