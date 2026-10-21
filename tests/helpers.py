from contextlib import contextmanager
from email.message import Message
from io import BytesIO
import json

from bleo._http import Response


class Raw(BytesIO):
    def __init__(self, body=b'', status=200, headers=None, chunk_size=None):
        super().__init__(body)
        self.status = status
        self.headers = Message()
        for name, value in (headers or {}).items():
            self.headers[name] = value
        self.chunk_size = chunk_size

    def getcode(self):
        return self.status

    def read1(self, size=-1):
        return self.read(min(size, self.chunk_size) if self.chunk_size else size)


def sse(*objects):
    return ''.join('data: ' + (obj if isinstance(obj, str) else json.dumps(obj)) + '\n\n'
                   for obj in objects).encode()


def chunk(text=None, finish=None, model='served-model'):
    delta = {} if text is None else {'content': text}
    return {'model': model, 'choices': [{'delta': delta, 'finish_reason': finish}]}


def completion(text='OK'):
    return Raw(sse(chunk(''), chunk(text), chunk(finish='stop'), '[DONE]'),
               headers={'Content-Type': 'text/event-stream'})


class ScriptedTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.closed = False

    @contextmanager
    def stream(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if not self.responses:
            raise AssertionError('Unexpected extra request')
        raw = self.responses.pop(0)
        if isinstance(raw, BaseException):
            raise raw
        try:
            yield Response(raw)
        finally:
            raw.close()

    def close(self):
        self.closed = True

    def payload(self, index=0):
        return json.loads(self.calls[index][2]['content'])
