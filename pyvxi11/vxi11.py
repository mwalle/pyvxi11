#
# Pure python VXI-11 client
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

import logging
import rpc

DEVICE_CORE_PROG = 0x0607af
DEVICE_CORE_VERS = 1
DEVICE_ASYNC_PROG = 0x0607b0
DEVICE_ASYNC_VERS = 1
DEVICE_INTR_PROG = 0x0607b1
DEVICE_INTR_VERS = 1

CREATE_LINK = 10
DEVICE_WRITE = 11
DEVICE_READ = 12
DEVICE_READSTB = 13
DEVICE_TRIGGER = 14
DEVICE_CLEAR = 15
DEVICE_REMOTE = 16
DEVICE_LOCAL = 17
DEVICE_LOCK = 18
DEVICE_UNLOCK = 19
DEVICE_ENABLE_SRQ = 20
DEVICE_DOCMD = 22
DESTROY_LINK = 23
CREATE_INTR_CHAN = 25
DESTROY_INTR_CHAN = 26

ERR_NO_ERROR = 0
ERR_INVALID_LINK_IDENTIFIER = 4
ERR_PARAMETER_ERROR = 5
ERR_DEVICE_LOCKED_BY_ANOTHER_LINK = 11
ERR_IO_TIMEOUT = 15
ERR_IO_ERROR = 17
ERR_ABORT = 23

OP_FLAG_WAIT_BLOCK = 1
OP_FLAG_END = 8
OP_FLAG_TERMCHAR_SET = 128

REASON_REQCNT = 1
REASON_CHR = 2
REASON_END = 4

def chunks(d, n):
    for i in xrange(0, len(d), n):
        yield d[i:i+n]

log = logging.getLogger(__name__)

class Vxi11Packer(rpc.RpcPacker):
    def pack_device_link(self, link):
        self.pack_int(link)

    def pack_create_link_parms(self, params):
        id, lock_device, lock_timeout, device = params
        self.pack_int(id)
        self.pack_bool(lock_device)
        self.pack_uint(lock_timeout)
        self.pack_string(device)

    def pack_device_write_parms(self, params):
        link, io_timeout, lock_timeout, flags, data = params
        self.pack_device_link(link)
        self.pack_uint(io_timeout)
        self.pack_uint(lock_timeout)
        self.pack_int(flags)
        self.pack_opaque(data)

    def pack_device_read_parms(self, params):
        link, request_size, io_timeout, lock_timeout, flags, term_char = params
        self.pack_device_link(link)
        self.pack_uint(request_size)
        self.pack_uint(io_timeout)
        self.pack_uint(lock_timeout)
        self.pack_int(flags)
        self.pack_int(term_char)


class Vxi11Unpacker(rpc.RpcUnpacker):
    def unpack_device_link(self):
        return self.unpack_int()

    def unpack_device_error(self):
        return self.unpack_int()

    def unpack_create_link_resp(self):
        error = self.unpack_int()
        link = self.unpack_device_link()
        abort_port = self.unpack_uint()
        max_recv_size = self.unpack_uint()
        return error, link, abort_port, max_recv_size

    def unpack_device_write_resp(self):
        error = self.unpack_int()
        size = self.unpack_uint()
        return error, size

    def unpack_device_read_resp(self):
        error = self.unpack_int()
        reason = self.unpack_int()
        data = self.unpack_opaque()
        return error, reason, data


class Vxi11Client(rpc.RawTCPClient):
    def __init__(self, host):
        self.packer = Vxi11Packer()
        self.unpacker = Vxi11Unpacker('')
        pmap = rpc.TCPPortMapperClient(host)
        mapping = (DEVICE_CORE_PROG, DEVICE_CORE_VERS, rpc.IPPROTO_TCP, 0)
        port = pmap.get_port(mapping)
        pmap.close()
        log.debug('VXI-11 uses port %d', port)

        rpc.RawTCPClient.__init__(self, host, DEVICE_CORE_PROG,
                DEVICE_CORE_VERS, port)

    def create_link(self, id, lock_device, lock_timeout, name):
        params = (id, lock_device, lock_timeout, name)
        return self.make_call(CREATE_LINK, params,
                self.packer.pack_create_link_parms,
                self.unpacker.unpack_create_link_resp)

    def device_write(self, link, io_timeout, lock_timeout, flags, data):
        params = (link, io_timeout, lock_timeout, flags, data)
        return self.make_call(DEVICE_WRITE, params,
                self.packer.pack_device_write_parms,
                self.unpacker.unpack_device_write_resp)

    def device_read(self, link, request_size, io_timeout, lock_timeout, flags,
            term_char):
        params = (link, request_size, io_timeout, lock_timeout, flags,
                term_char)
        return self.make_call(DEVICE_READ, params,
                self.packer.pack_device_read_parms,
                self.unpacker.unpack_device_read_resp)

    def destroy_link(self, link):
        return self.make_call(DESTROY_LINK, link,
                self.packer.pack_device_link,
                self.unpacker.unpack_device_error)


class Vxi11Error(Exception):
    pass


class Vxi11:
    def __init__(self, host, name=None, client_id=None):
        self.host = host
        self.io_timeout = 2
        self.lock_timeout = 2
        self.vxi11_client = Vxi11Client(host)
        self.client_id = client_id
        if name is None:
            self.name = 'inst0'
        else:
            self.name = name

    def open(self):
        log.info('Opening connection to %s', self.host)

        # If no client id was given, get it from the Vxi11 object
        client_id = self.client_id
        if client_id is None:
            client_id = id(self) & 0x7fffffff
        error, link_id, abort_port, max_recv_size = \
                self.vxi11_client.create_link(client_id, 0, 0, self.name)

        if error != 0:
            raise RuntimeError('TBD')

        # Some devices seem to return -1, but max_recv_size is unsigned.
        # As a workaround we set an upper boundary of 16k
        max_recv_size = min(max_recv_size, 16*1024)

        log.debug('link id is %d, max_recv_size is %d',
                link_id, max_recv_size)

        self.link_id = link_id
        self.max_recv_size = max_recv_size

    def close(self):
        log.info('Close connection to %s', self.host)
        self.vxi11_client.destroy_link(self.link_id)
        self.vxi11_client.close()

    def write(self, message):
        log.debug('Writing %d bytes (%s)', len(message), message)
        io_timeout = self.io_timeout * 1000       # in ms
        lock_timeout = self.lock_timeout * 1000   # in ms
        flags = 0
        # split into chunks
        msg_chunks = list(chunks(message, self.max_recv_size))
        for (n,chunk) in enumerate(msg_chunks):
            if n == len(msg_chunks)-1:
                flags = OP_FLAG_END
            else:
                flags = 0
            error, size = self.vxi11_client.device_write(self.link_id,
                    io_timeout, lock_timeout, flags, chunk)
            if error != ERR_NO_ERROR:
                raise Vxi11Error(error)
            assert size == len(chunk)

    def ask(self, message):
        self.write(message)
        return self.read()

    def read(self):
        read_size = self.max_recv_size
        io_timeout = self.io_timeout * 1000       # in ms
        lock_timeout = self.lock_timeout * 1000   # in ms
        reason = 0
        flags = 0
        term_char = 0
        data_list = list()
        while reason == 0:
            error, reason, data = self.vxi11_client.device_read(self.link_id,
                    read_size, io_timeout, lock_timeout, flags, term_char)
            if error != ERR_NO_ERROR:
                raise Vxi11Error(error)
            data_list.append(data)
            log.debug('Received %d bytes', len(data))

            if reason & REASON_REQCNT:
                reason &= ~REASON_REQCNT

        return ''.join(data_list)
