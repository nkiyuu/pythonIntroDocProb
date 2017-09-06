#!/usr/bin/env python

import json
import re
import threading
import tempfile
import tornado.ioloop
import tornado.web
from subprocess import Popen, PIPE


def check(data):
    blacklist = [
        'UnicodeDecodeError', 'intern', 'FloatingPointError', 'UserWarning',
        'PendingDeprecationWarning', 'any', 'EOFError', 'next', 'AttributeError',
        'ArithmeticError', 'UnicodeEncodeError', 'get_ipython', 'bin', 'map',
        'bytearray', '__name__', 'SystemError', 'set', 'NameError', 'Exception',
        'ImportError', 'basestring', 'GeneratorExit', 'float', 'BaseException',
        'IOError', 'id', 'hex', 'input', 'reversed', 'RuntimeWarning', '__package__',
        'del', 'yield', 'ReferenceError', 'chr', '__doc__', 'setattr',
        'KeyboardInterrupt', '__IPYTHON__', '__debug__', 'from', 'IndexError',
        'coerce', 'False', 'eval', 'repr', 'LookupError', 'file', 'MemoryError',
        'None', 'SyntaxWarning', 'max', 'list', 'pow', 'callable', 'len',
        'NotImplementedError', 'BufferError', '__import__', 'FutureWarning', 'buffer',
        'def', 'unichr', 'vars', 'globals', 'xrange', 'ImportWarning', 'dreload',
        'issubclass', 'exec', 'UnicodeError', 'raw_input', 'isinstance', 'finally',
        'Ellipsis', 'DeprecationWarning', 'return', 'OSError', 'complex', 'locals',
        'format', 'super', 'ValueError', 'reload', 'round', 'object', 'StopIteration',
        'ZeroDivisionError', 'memoryview', 'enumerate', 'slice', 'delattr',
        'AssertionError', 'EnvironmentError', 'property', 'zip', 'apply', 'long',
        'except', 'lambda', 'filter', 'assert', 'copyright', 'bool', 'BytesWarning',
        'getattr', 'dict', 'type', 'oct', '__IPYTHON__active', 'NotImplemented',
        'iter', 'hasattr', 'UnicodeTranslateError', 'bytes', 'abs', 'credits', 'min',
        'TypeError', 'execfile', 'SyntaxError', 'classmethod', 'cmp', 'tuple',
        'compile', 'try', 'all', 'open', 'divmod', 'staticmethod', 'license', 'raise',
        'Warning', 'frozenset', 'global', 'StandardError', 'IndentationError',
        'reduce', 'range', 'hash', 'KeyError', 'help', 'SystemExit', 'dir', 'ord',
        'True', 'UnboundLocalError', 'UnicodeWarning', 'TabError', 'RuntimeError',
        'sorted', 'sum', 'class', 'OverflowError'
    ]
    for entry in blacklist:
        if entry in data:
            return False
    whitelist = re.compile("^[\r\na-z0-9#\t.\[\]\'(),+*/:%><= _\\\-]*$", re.DOTALL)
    return bool(whitelist.match(data))


class ProcessHandler(threading.Thread):

    def ready(self):
        if self.timeout:
            self.request.write(json.dumps({
                "error": "timeout"
            }))
        else:
            self.request.write(json.dumps({
                "stdout": self.stdout,
                "stderr": self.stderr,
            }))
        self.request.finish()

    def run(self):
        self.stdout = self.stderr = ""
        self.timeout = False

        def proc_thread():
            proc.wait()
            self.stdout = proc.stdout.read()
            self.stderr = proc.stderr.read()
            tornado.ioloop.IOLoop.instance().add_callback(self.ready)
        _, tmpfile = tempfile.mkstemp()
        with open(tmpfile, "w") as fileobj:
            fileobj.write(self.code)
        proc = Popen(["/usr/bin/python", tmpfile], stdout=PIPE, stderr=PIPE)
        t = threading.Thread(target=proc_thread)
        t.start()
        t.join(2)
        if proc.poll() is None:
            self.timeout = True
            proc.kill()


class ExecHandler(tornado.web.RequestHandler):

    @tornado.web.asynchronous
    def post(self):
        self.set_header('Content-Type', "application/json")
        code = self.get_argument("code")
        print(code)
        if check(code):
            t = ProcessHandler()
            t.code = code
            t.request = self
            t.daemon = True
            t.start()
        else:
            self.write(json.dumps({"error": "forbidden"}))
            self.finish()


def main():
    app = tornado.web.Application([
        (r"/exec", ExecHandler),
        (r"/", tornado.web.RedirectHandler, {"url": "/index.html"}),
        (r"/(.*)", tornado.web.StaticFileHandler, {'path': "static/"})
    ])
    app.listen(8080)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
