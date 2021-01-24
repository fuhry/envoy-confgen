#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="envoyzkfp",
    version="0.1.0",
    license='MIT',
    packages=find_packages(),
    scripts=['envoy-zkfp'],
    install_requires=[
        'PyYAML>=5.0',
    ],
    author='Dan Fuhry',
    author_email='dan@fuhry.com',
    url='https://github.com/fuhry/openssh-ldap-authkeys',
)
