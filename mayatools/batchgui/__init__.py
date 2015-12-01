import json
import os
import random
import subprocess
import sys
import select
import time
import socket


def log(msg, *args):
    if args:
        msg = msg % args
    sys.stderr.write('[mayatools.batchgui:server] %s\n' % msg)
    sys.stderr.flush()


def find_maya(version=2014):
    if sys.platform.startswith("darwin"):
        roots = [
            '/opt/autodesk/maya%s/Maya.app/Contents' % version,
            '/Applications/Autodesk/maya%s/Maya.app/Contents' % versionm
        ]
    else:
        roots = [
            '/opt/autodesk/maya%s-x64' % version,
        ]
    for root in roots:
        path = os.path.join(root, 'bin', 'maya')
        if os.path.exists(path):
            return path
    raise ValueError('could not find maya')


class BatchGuiMaya(object):

    def __init__(self, path=None):
        self.path = path or find_maya()
        self.proc = None
        self.xvfb = None

    def __del__(self):
        if self.proc:
            self.proc.kill()
        if self.xvfb:
            self.xvfb.kill()

    def open(self):

        if self.proc:
            return

        env = os.environ.copy()

        if sys.platform.startswith('linux'):
            display = ':%d' % random.randrange(100, 200)
            log('Starting Xvfb as %s', display)
            # Maya seems to require 16bit. I can't get it to open files when
            # at any of 8, 24, or 32.
            self.xvfb = subprocess.Popen(['Xvfb', display, '-screen', '0', '1920x1080x16'])
            env['DISPLAY'] = display
            time.sleep(1)

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for _ in xrange(10):
            port = random.randrange(2000, 60000)
            server_sock.bind(('', port))
            break
        server_sock.listen(1)

        env['MAYATOOLS_BATCHGUI_PORT'] = str(port)

        the_corner = os.path.abspath(os.path.join(__file__, '..', 'the_corner'))
        log('Using runtime from %s', the_corner)
        env['PYTHONPATH'] = '%s:%s' % (
            the_corner,
            env.get('PYTHONPATH', ''),
        )

        log('Starting Maya at %s', self.path)
        self.proc = subprocess.Popen([self.path], env=env, cwd=the_corner)

        # Make sure we can communicate.
        log('Waiting for Maya...')
        server_sock.settimeout(30)
        self.sock, _ = server_sock.accept()
        self.sockf = os.fdopen(self.sock.fileno())
        token = os.urandom(8).encode('hex')
        log('Shaking hands with client...')
        self._send(type='hello', token=token)
        msg = self._recv(30) # Takes a while to get to idle
        if not msg:
            raise ValueError('no handshake from Maya')
        if msg != {'type': 'olleh', 'token': token}:
            raise ValueError('bad handshake from Maya', msg)
        log('Handshake complete; ready for commands.')

    def _recv(self, timeout=None):
        if timeout is not None:
            r, _, _ = select.select([self.sock], (), (), timeout)
            if not r:
                return
        msg = self.sockf.readline()
        if msg:
            return json.loads(msg)
        else:
            raise EOFError()

    def _send(self, **kwargs):
        if not self.proc:
            self.open()
        self.sock.send('%s\n' % json.dumps(kwargs))

    def eval(self, source):
        self._send(type='eval', source=source)
        msg = self._recv()
        if msg['type'] != 'eval_response':
            raise RuntimeError('bad message from Maya', msg)
        if 'exc_type' in msg:
            raise ValueError('exception from batch', msg['exc_type'], msg['exc_args'])
        return msg['value']

    def execfile(self, path):
        self._send(type='execfile', path=path)
        msg = self._recv()
        if msg['type'] != 'execfile_response':
            raise RuntimeError('bad message from Maya', msg)
        if 'exc_type' in msg:
            raise ValueError('exception from batch', msg['exc_type'], msg['exc_args'])

    def call(self, func, *args, **kwargs):
        if not isinstance(func, basestring):
            func = '%s:%s' % (func.__module__, func.__name__)
        self._send(type='call', func=func, args=args, kwargs=kwargs)
        msg = self._recv()
        if msg['type'] != 'call_response':
            raise RuntimeError('bad message from Maya', msg)
        if 'exc_type' in msg:
            raise ValueError('exception from batch', msg['exc_type'], msg['exc_args'])
        return msg['value']

    def exit(self, code=0):
        self._send(type='exit', code=code)
        log('Waiting for Maya to exit...')
        try:
            while True:
                if not self._recv(10):
                    break
        except EOFError:
            pass
        log('Maya has exited.')



