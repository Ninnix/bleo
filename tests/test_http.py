import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch
import zlib

from bleo._http import Response, Session
from helpers import Raw


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = 'città 🦆\nseconda riga\n'.encode()
        status = 503 if self.path == '/error' else 200
        self.send_response(status)
        if self.path == '/gzip':
            body = gzip.compress(body)
            self.send_header('Content-Encoding', 'gzip')
        elif self.path == '/deflate':
            body = zlib.compress(body)
            self.send_header('Content-Encoding', 'deflate')
        elif self.path == '/cookie':
            self.send_header('Set-Cookie', 'test=present; Path=/')
        elif self.path == '/echo-cookie':
            body = self.headers.get('Cookie', '').encode()
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        response = json.dumps({'body': body.decode(), 'header': self.headers.get('X-Test')}).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.session = Session(timeout=2, headers={'X-Test': 'default'})
        self.addCleanup(self.session.close)

    def test_post_utf8_and_header_overrides(self):
        with self.session.stream('POST', self.base + '/echo', content='città', headers={'X-Test': 'custom'}) as response:
            self.assertEqual(json.loads(response.text), {'body': 'città', 'header': 'custom'})
        self.assertTrue(response.raw.closed)

    def test_get_buffers_before_closing(self):
        response = self.session.get(self.base + '/')
        self.assertTrue(response.raw.closed)
        self.assertEqual(response.text, 'città 🦆\nseconda riga\n')
        self.assertEqual(response.read(), response.read())

    def test_http_errors_remain_readable_responses(self):
        response = self.session.get(self.base + '/error')
        self.assertEqual(response.status_code, 503)
        self.assertIn('seconda riga', response.text)
        self.assertTrue(response.raw.closed)

    def test_cookie_jar_roundtrip_and_close(self):
        self.session.get(self.base + '/cookie')
        self.assertEqual(self.session.get(self.base + '/echo-cookie').text, 'test=present')
        self.session.close()
        self.assertEqual(len(self.session.cookies), 0)

    def test_gzip_and_deflate_network_responses(self):
        for path in ('/gzip', '/deflate'):
            with self.subTest(path=path), self.session.stream('GET', self.base + path) as response:
                self.assertEqual(list(response.iter_lines()), ['città 🦆', 'seconda riga'])

    def test_unicode_and_crlf_across_byte_boundaries(self):
        raw = Raw('città 🦆\r\n\r\nfine'.encode(), chunk_size=1)
        self.assertEqual(list(Response(raw).iter_lines()), ['città 🦆', '', 'fine'])

    def test_compressed_chunks_preserve_utf8_lines(self):
        for encoding, encode in [('gzip', gzip.compress), ('deflate', zlib.compress)]:
            raw = Raw(encode('città 🦆\n'.encode()), headers={'Content-Encoding': encoding}, chunk_size=1)
            with self.subTest(encoding=encoding):
                self.assertEqual(list(Response(raw).iter_lines()), ['città 🦆'])

    def test_truncated_corrupt_and_unsupported_encoding_raise(self):
        cases = [(gzip.compress(b'hello')[:-4], 'gzip'), (b'not gzip', 'gzip'), (b'anything', 'br')]
        for body, encoding in cases:
            with self.subTest(encoding=encoding), self.assertRaises(OSError):
                Response(Raw(body, headers={'Content-Encoding': encoding})).read()

    def test_stream_closes_on_consumer_error(self):
        raw = Raw(b'test')
        with patch.object(self.session.opener, 'open', return_value=raw):
            with self.assertRaises(RuntimeError):
                with self.session.stream('GET', 'https://example.test'):
                    raise RuntimeError('consumer failed')
        self.assertTrue(raw.closed)

    def test_open_propagates_transport_errors(self):
        with patch.object(self.session.opener, 'open', side_effect=OSError('offline')):
            with self.assertRaises(OSError):
                self.session.get('https://example.test')

    def test_explicit_proxy_handles_both_schemes(self):
        with patch('bleo._http.build_opener') as opener:
            Session(proxy='http://localhost:8080')
            proxy_handler = opener.call_args.args[-1]
            self.assertEqual(proxy_handler.proxies,
                             {'http': 'http://localhost:8080', 'https': 'http://localhost:8080'})
        with self.assertRaises(ValueError):
            Session(proxy='socks5://localhost:8080')

    def test_per_request_timeout(self):
        raw = Raw(b'OK')
        with patch.object(self.session.opener, 'open', return_value=raw) as opener:
            self.session.get('https://example.test', timeout=9)
        self.assertEqual(opener.call_args.kwargs['timeout'], 9)
