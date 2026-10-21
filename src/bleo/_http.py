from contextlib import contextmanager
from http.cookiejar import Cookie, CookieJar
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener
import zlib


class Cookies(CookieJar):
    def set(self, name, value, domain):
        self.set_cookie(Cookie(0, name, value, None, False, domain, True,
                               domain.startswith('.'), '/', True, True, None,
                               True, None, None, {}, False))


class Response:
    def __init__(self, raw):
        self.raw = raw
        self.status_code = raw.getcode()
        self.headers = raw.headers
        self._body = None

    def chunks(self):
        encoding = self.headers.get('Content-Encoding', '').lower()
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS) if encoding == 'gzip' else zlib.decompressobj() if encoding == 'deflate' else None
        if encoding not in ('', 'identity', 'gzip', 'deflate'):
            raise OSError(f'Unsupported content encoding: {encoding}')
        read = getattr(self.raw, 'read1', self.raw.read)
        while True:
            chunk = read(8192)
            if not chunk:
                break
            try:
                yield decoder.decompress(chunk) if decoder else chunk
            except zlib.error as error:
                raise OSError('Invalid compressed response') from error
        if decoder:
            yield decoder.flush()
            if not decoder.eof:
                raise OSError('Truncated compressed response')

    def read(self):
        if self._body is None:
            self._body = b''.join(self.chunks())
        return self._body

    @property
    def text(self):
        return self.read().decode('utf-8', 'replace')

    def iter_lines(self):
        pending = b''
        for chunk in self.chunks():
            pending += chunk
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                yield line.rstrip(b'\r').decode('utf-8', 'replace')
        if pending:
            yield pending.decode('utf-8', 'replace')


class Session:
    def __init__(self, *, headers=None, timeout=60, proxy=None):
        self.headers = headers or {}
        self.timeout = timeout
        self.cookies = Cookies()
        handlers = [HTTPCookieProcessor(self.cookies)]
        if proxy:
            if urlsplit(proxy).scheme not in ('http', 'https'):
                raise ValueError('Use an HTTP or HTTPS proxy')
            handlers.append(ProxyHandler({'http': proxy, 'https': proxy}))
        self.opener = build_opener(*handlers)

    def open(self, method, url, *, headers=None, content=None, timeout=None):
        body = content.encode('utf-8') if isinstance(content, str) else content
        request = Request(url, data=body, headers={**self.headers, **(headers or {})}, method=method)
        try:
            raw = self.opener.open(request, timeout=self.timeout if timeout is None else timeout)
        except HTTPError as error:
            raw = error
        return Response(raw)

    def get(self, url, **kwargs):
        response = self.open('GET', url, **kwargs)
        try:
            response.read()
            return response
        finally:
            response.raw.close()

    @contextmanager
    def stream(self, method, url, **kwargs):
        response = self.open(method, url, **kwargs)
        try:
            yield response
        finally:
            response.raw.close()

    def close(self):
        self.cookies.clear()
