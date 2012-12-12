import base64
import pickle
import glob
import socket
import os
import select
import re
import tempfile
import functools


class CmdsProxy(object):

    def __init__(self, proc):
        self._proc = proc

    def __getattr__(self, name):
        return functools.partial(self._proc.call, 'maya.cmds:%s' % name)


class CommandPort(object):

    def __init__(self, addr=None):
        
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        for addr in glob.glob('/var/tmp/maya.*.pysock'):
            try:
                self._sock.connect(addr)
            except socket.error:
                continue
            else:
                break
        else:
            raise ValueError('no Maya sockets in /var/tmp')
        
        self._buffer = ''

        # Setup a child socket.
        self._tempfile = tempfile.NamedTemporaryFile(suffix='.pysock')
        self._send('cmds.commandPort(name=%r, sourceType="python")\n' % self._tempfile.name)
        self._recv(1)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.connect(self._tempfile.name)

        # Setup command proxy.
        self.cmds = CmdsProxy(self)


    def __del__(self):
        self._send('cmds.commandPort(name=%r, close=True)\n' % self._tempfile.name)

    def _send(self, msg):
        while msg:
            sent = self._sock.send(msg)
            if not sent:
                raise RuntimeError('didnt send anything')
            msg = msg[sent:]

    def _recv(self, timeout=None):
        while '\0' not in self._buffer:
            rlist, _, _ = select.select([self._sock], [], [], timeout)
            if not rlist:
                raise RuntimeError('timeout')
            self._buffer += self._sock.recv(8096)
        msg, self._buffer = self._buffer.split('\0', 1)
        return msg

    def call(self, func, *args, **kwargs):
        package = base64.b64encode(pickle.dumps((func, args, kwargs)))
        expr = '__import__(%r, fromlist=["."]).dispatch(%r)\n' % (__name__, package)
        self._send(expr)
        res = self._recv(1)
        res = pickle.loads(base64.b64decode(res))
        if res.get('status') == 'ok':
            return res['res']
        if res.get('status') == 'exception':
            raise res['type'](*res['args'])
        raise RuntimeError('bad response: %r' % res)

    def eval(self, expr, *args):
        return self.call(eval, *args)

    def mel(self, expr):
        return self.call('maya.mel:eval', expr)


# Convenient!
open = CommandPort


def _get_func(spec):
    if not isinstance(spec, basestring):
        return spec
    m = re.match(r'([\w\.]+):([\w]+)$', spec)
    if not m:
        raise ValueError('string funcs must be for form "package.module:function"')
    mod_name, func_name = m.groups()
    mod = __import__(mod_name, fromlist=['.'])
    return getattr(mod, func_name)


def dispatch(package):
    func, args, kwargs = pickle.loads(base64.b64decode(package))
    func = _get_func(func)
    try:
        print func, args, kwargs
        res = dict(status='ok', res=func(*args, **kwargs))
    except Exception as e:
        res = dict(status='exception', type=e.__class__, args=e.args)
    return base64.b64encode(pickle.dumps(res))



