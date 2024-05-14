""" Sudoku HTTP Server"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
from sudoku import Sudoku


class sudokuHTTP(BaseHTTPRequestHandler):
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        super().__init__(*args, **kwargs)


    def do_POST(self):
        if self.path == '/solve':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            sudoku = json.loads(post_data)
            # print(sudoku)
            # self.callback(sudoku) # chamar o callback
            # receive what comes from the callback
            solved_sudoku = self.callback(sudoku)
            # build a json response
            response = {'solved': True, 'sudoku': solved_sudoku}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())

    def do_GET(self):
        if self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'uptime': time.time()}).encode())
        elif self.path == '/network':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'network': 'localhost'}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())


class CustomSudokuHTTP(sudokuHTTP):
    def __init__(self, callback, *args, **kwargs):
        super().__init__(callback, *args, **kwargs)


# server = HTTPServer(('localhost', 8080), sudokuHTTP)
# print('Server running ...')
# server.serve_forever()
# server.server_close()
# print('Server stopped.')