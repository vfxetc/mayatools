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
        return functools.partial(self._proc, 'maya.cmds:%s' % name)


class CommandSock(object):

    def __init__(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.buffer = ''

    def send(self, msg):
        while msg:
            _, wlist, _ = select.select([], [self.sock], [], 0.1)
            if not wlist:
                raise RuntimeError('timeout')
            sent = self.sock.send(msg)
            if not sent:
                # I'm not sure if we will ever hit this...
                raise RuntimeError('socket did not accept data')
            msg = msg[sent:]

    def recv(self, timeout=None):
        while '\0' not in self.buffer:
            rlist, _, _ = select.select([self.sock], [], [], timeout)
            if not rlist:
                raise RuntimeError('timeout')
            self.buffer += self.sock.recv(8096)
        msg, self.buffer = self.buffer.split('\0', 1)
        return msg

    def __getattr__(self, name):
        return getattr(self.sock, name)


class CommandPort(object):

    def __init__(self, addr=None):
        
        sock = CommandSock()

        if addr:
            sock.connect(addr)
        else:
            for addr in glob.glob('/var/tmp/maya.*.pysock'):
                try:
                    sock.connect(addr)
                except socket.error:
                    continue
                else:
                    break
            else:
                raise ValueError('no Maya sockets in /var/tmp')

        # Setup a dedicated commandPort.
        self._tempfile = tempfile.NamedTemporaryFile(suffix='.pysock')
        sock.send('cmds.commandPort(name=%r, sourceType="python")\n' % self._tempfile.name)
        sock.recv(1)
        self.sock = CommandSock()
        self.sock.connect(self._tempfile.name)

        # Setup command proxy.
        self.cmds = CmdsProxy(self)


    def __del__(self):
        self.sock.send('cmds.commandPort(name=%r, close=True)\n' % self._tempfile.name)

    def call(self, func, args=None, kwargs=None, timeout=None):
        package = base64.b64encode(pickle.dumps((func, args or (), kwargs or {})))
        expr = '__import__(%r, fromlist=["."]).dispatch(%r)\n' % (__name__, package)
        self.sock.send(expr)
        res = self.sock.recv()
        res = pickle.loads(base64.b64decode(res))
        if res.get('status') == 'ok':
            return res['res']
        if res.get('status') == 'exception':
            raise res['type'](*res['args'])
        raise RuntimeError('bad response: %r' % res)

    def __call__(self, func, *args, **kwargs):
        return self.call(func, args, kwargs)

    def eval(self, expr, *args, **kwargs):
        return self.call(eval, args, **kwargs)

    def mel(self, expr, **kwargs):
        return self.call('maya.mel:eval', [expr], **kwargs)


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
        res = dict(status='ok', res=func(*args, **kwargs))
    except Exception as e:
        res = dict(status='exception', type=e.__class__, args=e.args)
    return base64.b64encode(pickle.dumps(res))



