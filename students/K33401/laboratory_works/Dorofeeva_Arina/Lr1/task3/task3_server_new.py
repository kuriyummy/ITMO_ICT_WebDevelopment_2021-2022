# -*- coding: cp1251 -*-
import json
import socket
import traceback
from email.parser import Parser
from functools import lru_cache
from urllib.parse import parse_qs, urlparse

MAX_HEADERS = 100
MAX_LINE = 64 * 1024


# ��������� �������
class MyHTTPServer:
    def __init__(self, host, port, server_name):
        self._host = host
        self._port = port
        self._server_name = server_name

        self._grades = {
            "����������": '100',
            "������������ �����������": '100',
            "����������������": '100',
            "�����������": '100',
            "������": '0',
        }

    # 1. ������ ������� �� ������, ��������� �������� ����������
    def serve_forever(self):
        serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto=0)  # create socket

        try:
            serv_sock.bind((self._host, self._port))  # open socket
            serv_sock.listen()  # open connection queue

            print(f'http://{self._host}:{self._port}/grades')  # print link

            while True:  # ������ � ����������� ����� ������������ ����� �������� ����������
                conn, _ = serv_sock.accept()  # accept connection
                try:
                    # ������ ���������� conn �������� ���������� �������.
                    # ����� ���������� ���������� ���������� ��������� HTTP-�������
                    self.serve_client(conn)
                except Exception as e:
                    print('Client serving failed', e)
        finally:
            serv_sock.close()

    # 2. ��������� ����������� �����������
    def serve_client(self, conn):
        try:
            # ������ � ������ HTTP-�������
            req = self.parse_request(conn)
            # ���������
            resp = self.handle_request(req)
            # �������� ������
            self.send_response(conn, resp)
        except ConnectionResetError:
            conn = None
        # � ������ ������ �� ����� �� ������, ��������� ������������� ��������� ��������� �� ������
        except Exception as e:
            self.send_error(conn, e)

        if conn:
            conn.close()  # close connection

    def parse_request_line(self, rfile):
        raw = rfile.readline(MAX_LINE + 1)  # ���������� ������ ������ �������
        if len(raw) > MAX_LINE:
            raise HTTPError(400, 'Bad request',
                            'Request line is too long')

        # ������ ������ ������, ��������� �� �� �����, ���� � ������ � ��������� �� � words
        req_line = str(raw, 'iso-8859-1')
        words = req_line.split()  # ��������� �� �������
        if len(words) != 3:  # � ������� ����� 3 �����
            raise HTTPError(400, 'Bad request',
                            'Malformed request line')

        method, target, ver = words
        if ver != 'HTTP/1.1':
            raise HTTPError(505, 'HTTP Version Not Supported')
        return words

    # 3. ������� ��� ��������� ��������� http+�������. Python, ����� ������������� ����������� ������� ������ ���� ��������� �������, ������� ������������� file object ���������. ��� ����� ����������� ��������� ���������� ������. ��������� ������ - ������ ������. ������ ������ ����� ������� �� 3 ��������  (����� + url + ������ ���������). URL ���������� ������� �� ����� � ��������� (isu.ifmo.ru/pls/apex/f?p=2143 , ��� isu.ifmo.ru/pls/apex/f, � p=2143 - �������� p �� ��������� 2143)
    def parse_request(self, conn):
        rfile = conn.makefile('rb')
        method, target, ver = self.parse_request_line(rfile)
        headers = self.parse_headers(rfile)
        host = headers.get('Host')
        # �������� ������� � ������������ ��������� Host
        if not host:
            raise Exception('Bad request')
        if host not in (self._host,
                        f'{self._host}:{self._port}'):
            raise Exception('Not found')
        return Request(method, target, ver, headers, rfile)

    # 4. ������� ��� ��������� headers. ���������� ��������� ��� ��������� ����� ������ ������ �� ��������� ������ ������ � ��������� �� � ������.
    def parse_headers(self, rfile):
        headers = []
        while True:
            # ������ ��������� ���������, ��������� �� �� ��� � ��������, ��������� � ������
            line = rfile.readline(MAX_LINE + 1)  # ���������� ������ ������ �������
            if len(line) > MAX_LINE:
                raise Exception('Header line is too long')

            if line in (b'\r\n', b'\n', b''):
                # ��������� ������ ����������
                break

            headers.append(line)
            if len(headers) > MAX_HEADERS:
                raise Exception('Too many headers')

        sheaders = b''.join(headers).decode('iso-8859-1')
        # ���������� ������ email.message.Message:
        # ����� � Message - ��� ��������������� � ������� ��������� ����� ����������.
        return Parser().parsestr(sheaders)

    # 5. ������� ��� ��������� url � ������������ � ������ �������. � ������ ������ ������, ����� ����� ������� ����� �������, ������� ������������ GET ��� POST ������. GET ������ ������ ���������� ������. POST ������ ������ ���������� ������ �� ������ ���������� ����������.
    def handle_request(self, req):
        if req.path == '/grades' and req.method == 'POST':
            return self.handle_post(req)

        if req.path == '/grades' and req.method == 'GET':
            return self.handle_get(req)

        raise Exception('Not found')

    def handle_get(self, req):
        accept = req.headers.get('Accept')
        if 'text/html' in accept:
            content_type = 'text/html; charset=utf-8'
            body = '<html><head><style>span {padding: 100px;}</style>�(</head><body>'
            for subject in self._grades:
                body += f'<div><span>{subject}: {self._grades[subject]}</span></div>'
            body += '</div></body></html>'

        else:
            return Response(406, 'Not Acceptable')

        body = body.encode('utf-8')
        headers = [('Content-Type', content_type),
                   ('Content-Length', len(body))]
        return Response(200, 'OK', headers, body)

    def handle_post(self, request):
        subject = request.query['subject'][0]
        grade = request.query['grade'][0]

        if subject not in self._grades:
            self._grades[subject] = []

        self._grades[subject].append(grade)

        return Response(200, 'OK')

    # 6. ������� ��� �������� ������. ���������� �������� � ���������� status line ���� HTTP/1.1 <status_code> <reason>. �����, ��������� �������� ��������� � ������ ������, ������������ ����� ������ ����������.
    def send_response(self, conn, resp):
        rfile = conn.makefile('wb')
        # ���������� � ���������� status line ���� HTTP/1.1 <status_code> <reason>
        status_line = f'HTTP/1.1 {resp.status} {resp.reason}\r\n'
        rfile.write(status_line.encode('iso-8859-1'))

        if resp.headers:
            # ��������� ���������� ���������
            for (key, value) in resp.headers:
                header_line = f'{key}: {value}\r\n'
                rfile.write(header_line.encode('iso-8859-1'))

        # ��������� ������ ������, ������������ ����� ������ ����������
        rfile.write(b'\r\n')

        # ��� ������� ���� ������ ���������� ��� � �����
        if resp.body:
            rfile.write(resp.body)

        rfile.flush()
        rfile.close()

    def send_error(self, conn, err):
        # � ������ ������������� ������ �� �������, ��� ����� ���������� ��������� �����
        try:
            status = err.status
            reason = err.reason
            body = (err.body or err.reason).encode('utf-8')
        except:
            status = 500
            traceback.print_exc()
            reason = b'Internal Server Error'
            body = b'Internal Server Error'
        resp = Response(status, reason,
                        [('Content-Length', len(body))],
                        body)
        self.send_response(conn, resp)


class HTTPError(Exception):
    def __init__(self, status, reason, body=None):
        super()
        self.status = status
        self.reason = reason
        self.body = body


class Request:
    def __init__(self, method, target, version, headers, rfile):
        self.method = method
        self.target = target
        self.version = version
        self.headers = headers
        self.rfile = rfile

    #  ������� ������ path � query, ������� ����� ��������� ���� ����
    #  /grades?subject=������&grade=0 �� /grades � {'subject': ['������'], 'grade': ['0']}, ��������������

    @property
    def path(self):
        return self.url.path

    @property
    @lru_cache(maxsize=None)
    def query(self):
        return parse_qs(self.url.query)

    @property
    @lru_cache(maxsize=None)
    def url(self):
        return urlparse(self.target)

    def body(self):
        size = self.headers.get('Content-Length')
        if not size:
            return None
        return self.rfile.read(size)


class Response:
    def __init__(self, status, reason, headers=None, body=None):
        self.status = status
        self.reason = reason
        self.headers = headers
        self.body = body


if __name__ == '__main__':
    host = "127.0.0.1"
    port = 3000
    name = "localhost"

    serv = MyHTTPServer(host, port, name)
    try:
        serv.serve_forever()
    except KeyboardInterrupt:
        pass
