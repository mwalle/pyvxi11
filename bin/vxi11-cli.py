#!/usr/bin/env python
#
# Simple VXI-11 commandline interface
# Copyright (c) 2011 Michael Walle
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Description:
# Commands are sent to the VXI-11 device after every newline. If the command
# ends in '?' the response is received.
#

import sys
import logging
import readline
from optparse import OptionParser

from pyvxi11 import Vxi11, Vxi11Error

def main():
    usage = 'usage: %prog [options] <host>'
    parser = OptionParser(usage=usage)
    parser.add_option('-d', action='store_true', dest='debug',
            help='enable debug messages')
    parser.add_option('-v', action='store_true', dest='verbose',
            help='be more verbose')

    (options, args) = parser.parse_args()

    logging.basicConfig()
    if options.verbose:
        logging.getLogger('pyvxi11').setLevel(logging.INFO)
    if options.debug:
        logging.getLogger('pyvxi11').setLevel(logging.DEBUG)

    if len(args) < 1:
        print parser.format_help()
        sys.exit(1)

    host = args[0]

    v = Vxi11(host)
    v.open()

    print "Enter command to send. Quit with 'q'."
    try:
        while True:
            cmd = raw_input('=> ')
            if cmd == 'q':
                break
            if len(cmd) > 0:
                is_query = cmd.split(' ')[0][-1] == '?'
                try:
                    if is_query:
                        print v.ask(cmd)
                    else:
                        v.write(cmd)
                except Vxi11Error, e:
                    print 'ERROR: %s' % e
    except EOFError:
        print 'exitting..'

    v.close()

if __name__ == '__main__':
    main()
