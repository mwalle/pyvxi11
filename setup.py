#!/usr/bin/env python

from setuptools import setup, find_packages

def main():
    setup(name = 'pyvxi11',
            version = '0.1',
            description = 'Pure python VXI-11 library',
            author = 'Michael Walle',
            author_email = 'michael@walle.cc',
			license = 'GPL 3+',
			url = 'http://github.com/mwalle/pyvxi11',
            packages = find_packages(exclude=['tests']),
            scripts = ['bin/vxi11-cli.py'],
            test_suite = 'tests',
    )

if __name__ == '__main__':
    main()
