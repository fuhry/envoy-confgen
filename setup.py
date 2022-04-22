#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="envoyconfgen",
    version="0.2.0",
    license='MIT',
    packages=find_packages(),
    scripts=['envoy-confgen'],
    install_requires=[
        'PyYAML>=5.0',
    ],
    author='Dan Fuhry',
    author_email='dan@fuhry.com',
    url='https://github.com/fuhry/envoy-confgen',
)
