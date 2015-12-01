import os
import threading
import time
import sys
import shutil
import traceback
import subprocess
import socket
import json

from maya import cmds


def log(msg, *args):
    if args:
        msg = msg % args
    sys.__stderr__.write('[mayatools.batchgui:client] %s\n' % msg)
    sys.__stderr__.flush()


def setup():
    
    global sock
    global sockf

    port = int(os.environ['MAYATOOLS_BATCHGUI_PORT'])
    sock = socket.create_connection(('127.0.0.1', port))
    sockf = os.fdopen(sock.fileno())

    log('Starting handler thread...')
    thread = threading.Thread(target=safe_call, args=(loop, ))
    thread.start()


def recv():
    msg = sockf.readline()
    if not msg:
        return
    return json.loads(msg)


def send(**kwargs):
    sock.send('%s\n' % json.dumps(kwargs))


def safe_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except:
        try:
            traceback.print_exc()
            os._exit(1)
        except:
            os._exit(2)
    else:
        os._exit(0)


def loop():
    while True:
        msg = recv()
        if not msg: # All done!
            log('No more messages!')
            return
        type_ = msg['type']
        log('Dispatching %s to main event loop.', type_)
        cmds.scriptJob(idleEvent=lambda: safe_call(dispatch, msg), runOnce=True)


def dispatch(msg):
    type_ = msg.pop('type')
    log('Calling handle_%s...', type_)
    handler = globals()['handle_%s' % type_]
    handler(**msg)


def handle_hello(token):
    send(type='olleh', token=token)


def handle_eval(source):
    try:
        res = eval(source)
    except Exception as e:
        traceback.print_exc()
        send(type='eval_response', exc_type=e.__class__.__name__, exc_args=e.args)
    else:
        send(type='eval_response', value=res)


def handle_execfile(path):
    try:
        execfile(path)
    except Exception as e:
        traceback.print_exc()
        send(type='execfile_response', exc_type=e.__class__.__name__, exc_args=e.args)
    else:
        send(type='execfile_response')


def handle_call(func, args=None, kwargs=None):
    from metatools.imports.entry_points import load_entry_point
    try:
        func = load_entry_point(func)
        res = func(*(args or ()), **(kwargs or {}))
    except Exception as e:
        traceback.print_exc()
        send(type='call_response', exc_type=e.__class__.__name__, exc_args=e.args)
    else:
        send(type='call_response', value=res)


def handle_exit(code=0):
    os._exit(code)

