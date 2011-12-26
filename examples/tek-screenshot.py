#!/usr/bin/env python
#
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

"""Take screenshots from a Tektronix DSO.

usage: tek-screenshot.py <host> <file.png>
"""

import pyvxi11
import sys
import time

if len(sys.argv) != 3:
    print __doc__
    sys.exit(1)

f = file(sys.argv[2], 'w')
v = pyvxi11.Vxi11(sys.argv[1])
v.open()
v.write(r'EXPORT:FILENAME "C:\TEMP\SCREEN.PNG"')
v.write('EXPORT:FORMAT PNG')
v.write('EXPORT:IMAGE NORMAL')
v.write('EXPORT:PALETTE COLOR')
v.write('EXPORT:VIEW FULLSCREEN')
#v.write('EXPORT:VIEW GRATICULE')
#v.write('EXPORT:VIEW FULLNO')
v.write('EXPORT START')
v.write(r'FILESYSTEM:PRINT "C:\TEMP\SCREEN.PNG", GPIB')
time.sleep(0.5)
f.write(v.read())
v.write(r'FILESYSTEM:DELETE "C:\TEMP\SCREEN.PNG"')

