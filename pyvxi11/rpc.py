#
# RPC and portmapper client
#
# Major parts of this file were stolen from Python RPC demo. Unfortunately,
# there is no author nor any licence.
# 
# Modified by Michael Walle <michael@walle.cc>
#
import xdrlib
import socket
import struct

RPCVERSION = 2

CALL = 0
REPLY = 1

AUTH_NULL = 0
AUTH_UNIX = 1
AUTH_SHORT = 2
AUTH_DES = 3

MSG_ACCEPTED = 0
MSG_DENIED = 1

SUCCESS = 0	           # RPC executed successfully
PROG_UNAVAIL = 1       # remote hasn't exported program
PROG_MISMATCH = 2      # remote can't support version #
PROC_UNAVAIL = 3       # program can't support procedure
GARBAGE_ARGS = 4       # procedure can't decode params

RPC_MISMATCH = 0       # RPC version number != 2
AUTH_ERROR = 1         # remote can't authenticate caller

AUTH_BADCRED = 1       # bad credentials (seal broken)
AUTH_REJECTEDCRED = 2  # client must begin new session
AUTH_BADVERF = 3       # bad verifier (seal broken)
AUTH_REJECTEDVERF = 4  # verifier expired or replayed
AUTH_TOOWEAK = 5       # rejected for security reasons

class RpcError(Exception):
    pass
class RpcGenericDecodeError(RpcError):
    pass
class RpcBadVersion(RpcError):
    pass
class RpcGarbageArgumentsError(RpcError):
    pass
class RpcProcedureUnavailableError(RpcError):
    pass
class RpcVersionMismatchError(RpcError):
    pass


def make_auth_null():
    return ''


class RpcPacker(xdrlib.Packer):
    def pack_auth(self, auth):
        flavor, stuff = auth
        self.pack_enum(flavor)
        self.pack_opaque(stuff)

    def pack_auth_unix(self, stamp, machinename, uid, gid, gids):
        self.pack_uint(stamp)
        self.pack_string(machinename)
        self.pack_uint(uid)
        self.pack_uint(gid)
        self.pack_uint(len(gids))
        for i in gids:
            self.pack_uint(i)

    def pack_callheader(self, xid, prog, vers, proc, cred, verf):
        self.pack_uint(xid)
        self.pack_enum(CALL)
        self.pack_uint(RPCVERSION)
        self.pack_uint(prog)
        self.pack_uint(vers)
        self.pack_uint(proc)
        self.pack_auth(cred)
        self.pack_auth(verf)
        # Caller must add procedure-specific part of call

    def pack_replyheader(self, xid, verf):
        self.pack_uint(xid)
        self.pack_enum(REPLY)
        self.pack_uint(MSG_ACCEPTED)
        self.pack_auth(verf)
        self.pack_enum(SUCCESS)
        # Caller must add procedure-specific part of reply

class RpcUnpacker(xdrlib.Unpacker):
    def unpack_auth(self):
        flavor = self.unpack_enum()
        stuff = self.unpack_opaque()
        return (flavor, stuff)

    def unpack_callheader(self):
        xid = self.unpack_uint(xid)
        mtype = self.unpack_enum()
        if mtype != CALL:
            raise RpcGenericDecodeError('No CALL but %d' % mtype)
        rpc_version = self.unpack_uint()
        if rpc_version != RPCVERSION:
            raise RpcBadVersion(rpc_version)
        prog = self.unpack_uint()
        vers = self.unpack_uint()
        proc = self.unpack_uint()
        cred = self.unpack_auth()
        verf = self.unpack_auth()
        return xid, prog, vers, proc, cred, verf
        # Caller must add procedure-specific part of call

    def unpack_replyheader(self):
        xid = self.unpack_uint()
        mtype = self.unpack_enum()

        if mtype != REPLY:
            raise RpcGenericDecodeError('No REPLY but %d' % mtype)

        reply_stat = self.unpack_enum()
        if reply_stat == MSG_DENIED:
            reject_stat = self.unpack_enum()
            if reject_stat == RPC_MISMATCH:
                low = self.unpack_uint()
                high = self.unpack_uint()
                raise RpcVersionMismatchError(high,low)
            elif reject_stat == AUTH_ERROR:
                auth_stat = self.unpack_uint()
                raise RpcAuthFailedError(auth_stat)
            raise RpcGenericDecodeError('unknown reject_stat %d', reject_stat)
        elif reply_stat != MSG_ACCEPTED:
            raise RpcGenericDecodeError('unknown reply_stat %d', reply_stat)

        verf = self.unpack_auth()
        accept_stat = self.unpack_enum()
        
        if accept_stat == PROG_UNAVAIL:
            raise RpcProgramUnavailableError()
        elif accept_stat == PROG_MISMATCH:
            low = self.unpack_uint()
            high = self.unpack_uint()
            raise RpcProgramMismatchError(high,low)
        elif accept_stat == PROC_UNAVAIL:
            raise RpcProcedureUnavailableError(high,low)
        elif accept_stat == GARBAGE_ARGS:
            raise RpcGarbageArgumentsError()
        elif accept_stat != SUCCESS:
            raise RpcGenericDecodeError('unknown accept_stat %d', accept_stat)
        return xid, verf
        # Caller must get procedure-specific part of reply


# Program number, version and (fixed!) port number
PMAP_PROG = 100000
PMAP_VERS = 2
PMAP_PORT = 111

# Procedure numbers
PMAPPROC_NULL = 0     # (void) -> void
PMAPPROC_SET = 1      # (mapping) -> bool
PMAPPROC_UNSET = 2    # (mapping) -> bool
PMAPPROC_GETPORT = 3  # (mapping) -> unsigned int
PMAPPROC_DUMP = 4     # (void) -> pmaplist
PMAPPROC_CALLIT = 5   # (call_args) -> call_result

# A mapping is (prog, vers, prot, port) and prot is one of:
IPPROTO_TCP = 6
IPPROTO_UDP = 17

# A pmaplist is a variable-length list of mappings, as follows:
# either (1, mapping, pmaplist) or (0).

# A call_args is (prog, vers, proc, args) where args is opaque;
# a call_result is (port, res) where res is opaque.


class PortMapperPacker(RpcPacker):
    def pack_mapping(self, mapping):
        prog, vers, prot, port = mapping
        self.pack_uint(prog)
        self.pack_uint(vers)
        self.pack_uint(prot)
        self.pack_uint(port)

    def pack_pmaplist(self, list):
        self.pack_list(list, self.pack_mapping)

    def pack_call_args(self, call_args):
        prog, vers, proc, args = call_args
        self.pack_uint(prog)
        self.pack_uint(vers)
        self.pack_uint(proc)
        self.pack_opaque(args)


class PortMapperUnpacker(RpcUnpacker):
    def unpack_mapping(self):
        prog = self.unpack_uint()
        vers = self.unpack_uint()
        prot = self.unpack_uint()
        port = self.unpack_uint()
        return prog, vers, prot, port

    def unpack_pmaplist(self):
        return self.unpack_list(self.unpack_mapping)

    def unpack_call_result(self):
        port = self.unpack_uint()
        res = self.unpack_opaque()
        return port, res


class RpcClient(object):
    def __init__(self, host, prog, vers, port):
        self.host = host
        self.prog = prog
        self.vers = vers
        self.port = port
        self.last_xid = 0
        self._credentials = None
        self._verifier = None

    @property
    def credentials(self):
        if self._credentials is None:
            self._credentials = (AUTH_NULL, make_auth_null())
        return self._credentials

    @credentials.setter
    def credentials(self, credentials):
        self._credentials = credentials

    @property
    def verifier(self):
        if self._verifier is None:
            self._verifier = (AUTH_NULL, make_auth_null())
        return self._verifier

    @verifier.setter
    def verifier(self, verifier):
        self._verifier = verifier

    def start_call(self, proc):
        self.last_xid = xid = self.last_xid + 1
        cred = self.credentials
        verf = self.verifier
        p = self.packer
        p.reset()
        p.pack_callheader(xid, self.prog, self.vers, proc, cred, verf)

    def make_call(self, proc, args, pack_func, unpack_func):
        if pack_func is None and args is not None:
            raise TypeError('Non-null args with null pack_func')
        self.start_call(proc)
        if pack_func:
            pack_func(args)
        self.do_call()
        if unpack_func:
            result = unpack_func()
        else:
            result = None
        self.unpacker.done()
        return result
        
    def call0(self):
        # Procedure 0 is always like this
        return self.make_call(0, None, None, None)


class RawTCPClient(RpcClient):
    def __init__(self, host, prog, vers, port):
        RpcClient.__init__(self, host, prog, vers, port)
        self.connect()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def close(self):
        self.sock.close()

    def send_record(self, record):
        header = struct.pack('>I', len(record) | 0x80000000)
        buf = header + record
        n_sent = 0
        while n_sent < len(buf):
            n_sent += self.sock.send(buf[n_sent:])

    def recv_record(self):
        record = list()
        last = False
        while not last:
            frag, last = self.recv_fragment()
            record.append(frag)
        return ''.join(record)

    def recv_fragment(self):
        header = self.sock.recv(4)
        if len(header) < 4:
            raise EOFError()
        length = struct.unpack('>I', header)[0]
        last = bool(length & 0x80000000)
        length &= 0x7fffffff

        buf = list()
        n_received = 0
        while n_received < length:
            b = self.sock.recv(length-n_received)
            n_received += len(b)
            buf.append(b)

        return ''.join(buf), last

    def do_call(self):
        buf = self.packer.get_buf()
        self.send_record(buf)
        reply = self.recv_record()
        self.unpacker.reset(reply)
        xid, verf = self.unpacker.unpack_replyheader()
        if xid != self.last_xid:
            # can't really happen since this is TCP
            raise RuntimeError('wrong xid in reply %d insted of %d' %
                    (xid, self.last_xid))


class CommonPortMapperClient:
    def __init__(self):
        self.packer = PortMapperPacker()
        self.unpacker = PortMapperUnpacker('')

    def set(self, mapping):
        return self.make_call(PMAPPROC_SET, mapping,
                self.packer.pack_mapping, self.unpacker.unpack_uint)

    def unset(self, mapping):
        return self.make_call(PMAPPROC_UNSET, mapping,
                self.packer.pack_mapping, self.unpacker.unpack_uint)

    def get_port(self, mapping):
        return self.make_call(PMAPPROC_GETPORT, mapping,
                self.packer.pack_mapping, self.unpacker.unpack_uint)

    def dump(self):
        return self.make_call(PMAPPROC_DUMP, None,
                None, self.unpacker.unpack_pmaplist)

    def callit(self, call_args):
        return self.make_call(PMAPPROC_CALLIT, call_args,
                self.packer.pack_call_args, self.unpacker.unpack_call_result)


class TCPPortMapperClient(CommonPortMapperClient, RawTCPClient):
    def __init__(self, host, port=PMAP_PORT):
        RawTCPClient.__init__(self, host, PMAP_PROG, PMAP_VERS, port)
        CommonPortMapperClient.__init__(self)
