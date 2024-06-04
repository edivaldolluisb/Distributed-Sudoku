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
            response = {'sudoku': solved_sudoku}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Page not found! Go to /solve istead'}).encode())

    def do_GET(self):
        if self.path == '/stats':

            # retornar os status da rede p2p
            status = self.callback('stats')

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        elif self.path == '/network':
            # retornar a lista de connexões
            network = self.callback('network')

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(network).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Page not found, check /stats or /network'}).encode())

# server = HTTPServer(('localhost', 8080), sudokuHTTP)
# print('Server running ...')
# server.serve_forever()
# server.server_close()
# print('Server stopped.')