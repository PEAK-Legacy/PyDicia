#!/usr/bin/env python
"""Distutils setup file"""
import sys
import ez_setup
ez_setup.use_setuptools()
from setuptools import setup

# Metadata
PACKAGE_NAME = "PyDicia"
PACKAGE_VERSION = "0.1a2"

def get_description():
    # Get our long description from the documentation
    f = file('README.txt')
    lines = []
    for line in f:
        if not line.strip():
            break     # skip to first blank line
    for line in f:
        if line.startswith('.. contents::'):
            break     # read to table of contents
        lines.append(line)
    f.close()
    return ''.join(lines)

setup(
    name=PACKAGE_NAME,
    version=PACKAGE_VERSION,
    description= "Print labels, envelopes, US postage, and more using the endicia.com API",
    long_description = file('README.txt').read(), #get_description(),
    url = "http://cheeseshop.python.org/pypi/PyDicia",
    author="Phillip J. Eby",
    author_email="peak@eby-sarna.com",
    license="PSF or ZPL",
    test_suite = 'pydicia',
    py_modules = ['pydicia'],
    install_requires = [
        'simplegeneric>=0.6', 'DecoratorTools>=1.4'
    ] + ['ElementTree'][:sys.version<'2.5']
)

