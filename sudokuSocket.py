'''Sudoku node socket'''
import selectors
import socket
import sys
import signal
import time
import threading

from sudokuHttp import sudokuHTTP
from sudokuHttp import CustomSudokuHTTP
from http.server import HTTPServer

from sudoku import Sudoku

import json

class Server:
    """Chat Server process."""

    def __init__(self, host="", port=5000, httpport=8000, connect_port: tuple = None):
        """Initialize server with host and port."""
        self.sel = selectors.DefaultSelector()
        
        self._host = host
        self._port = port
        self.connect_to = connect_port

        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        """Listen for incoming connections."""
        self.sock.bind((self._host, self._port))
        self.sock.listen(50)
        self.sock.setblocking(False)
        print(f"Listening on {self._host}:{self._port}")

        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)

        # http server
        self.http_server = HTTPServer(('localhost', httpport), lambda *args, **kwargs: CustomSudokuHTTP(self.sudoku_received, *args, **kwargs))

        # connection data
        self.connection = {self.sock}
        self.bind_connections = {}

    def accept(self, sock, mask):
        """Accept incoming connections."""
        print("Server is accepting.")
        conn, addr = sock.accept()  # Should be ready
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)
        self.connection.add(conn)
        # print(f'address: {addr}')

        print(f'got a connectio ffrom {conn}')
        # send  my list of connections address

        # join_message = {"command":"join_reply", "connections": [c.getpeername() for c in self.connection]}
        # conn.sendall(json.dumps(join_message).encode())
        print(conn.getpeername())
        # conn.sendall(b'Hello from server')

    def connect(self):
        """Connect to a peer"""
        try:
            connection = socket.create_connection(self.connect_to)
            self.connection.add(connection)

            print(f'connected to :{connection}')
            connection.setblocking(False)
            self.sel.register(connection, selectors.EVENT_READ, self.read)

            # create a bind point in the bind connections variable
            self.bind_connections[connection.getpeername()] = connection.getpeername()

            # send my join message
            mybind = f"{self._host}:{self._port}"
            join_message = {"command":"join", "bindPoint": mybind}
            connection.sendall(json.dumps(join_message).encode())

        except Exception as e:
            print(f'problema ao conectar!. Error : {e}')

    def read(self, conn, mask):
        """REad incomming messages"""
        try:
            data = conn.recv(1024)

            if data:
                try:
                    message = json.loads(data.decode())
                    print(f"Received message: {message}")

                    if message['command'] == 'join':
                        # add the connection to the bind connections
                        host, port = message['bindPoint'].split(':')
                        addr = (host, int(port))
                        self.bind_connections[conn.getpeername()] = addr

                        # send the list of bind connections values 
                        bind_points = list(self.bind_connections.values())
                        join_reply = {"command": "join_reply", "bindPoints": bind_points}
                        conn.sendall(json.dumps(join_reply).encode())

                        # imprime a lista de conexões atualizada
                        print(f'bind connections: {self.bind_connections}')

                    elif message['command'] == 'join_reply':
                        print(f'received points: {message["bindPoints"]}')
                        print(f'my bind points: {self.bind_connections}')

                        # connect to the other nodes
                        # for bind_point in message['bindPoints']:
                        #         host, port = bind_point.split(':')
                        #         addr = (host, int(port))
                        #         # check if it is not me and the the one who is sending the message
                        #         if addr != (self._host, self._port) and addr != conn.getpeername():
                        #             self.connect_to = addr
                        #             self.connect()
                        # print(f'my bind points: {self.bind_connections}')


                except json.JSONDecodeError as e:
                    print(f"Erro ao decodificar a mensagem JSON: {e}")


                print('mesg: ', data.decode())

            else:
                print(f'closing connection for:{conn.getpeername()}')

                self.sel.unregister(conn)
                conn.close()
                self.connection.remove(conn)

        except ConnectionResetError:
            print(f'conexão fechada abrumtamente por {conn.getpeername()}')
            self.sel.unregister(conn)
            conn.close()
            self.connection.remove(conn)

        except Exception as e:
            print(f'Erro ao ler os dados: {e}')
            self.shutdown(signal.SIGINT, None)
            sys.exit(1)

    def sudoku_received(self, sudoku):
        """processar o sudoku recibido por http"""
        print(f"Recebido sudoku: {sudoku} server")
        # print(sudoku.solve_sudoku(sudoku.puzzle()))
        sudoku_puzzle = Sudoku(sudoku)
        sudoku_puzzle.solve_sudoku(sudoku['sudoku'])
        return sudoku_puzzle.puzzle()

    def shutdown(self, signum, frame):
        """Shutdown server."""

        print("Server is shutting down.")
        # fechar conexões com outros nodes
        for conn in self.connection:
            self.sel.unregister(conn)
            conn.close()

        # self.sel.unregister(self.sock)
        # self.sock.close()
        self.http_server.server_close() # fechar o servidor http
        print("Server fechado.")
        sys.exit(0)

    # def listen(self):
    #     """Listen for incoming connections."""
    #     self.sock.bind((self._host, self._port))
    #     self.sock.listen(50)
    #     print(f"Listening on {self._host}:{self._port}")

    def loop(self):
        """Loop indefinetely."""
        # Start listening
        # listener_thread = threading.Thread(target=self.listen)
        # listener_thread.start()

        # connect to another node
        if self.connect_to is not None:
            time.sleep(1)
            self.connect()

        try:
            print('Sudoku server running ...')
            # start http server
            server_http_thread = threading.Thread(target=self.http_server.serve_forever)
            server_http_thread.start()

            while True:
                events = self.sel.select()
                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj, mask)
        
        except KeyboardInterrupt:
            self.shutdown(signal.SIGINT, None)
        except Exception as e:
            print(f'Erro: {e}')
            self.shutdown(signal.SIGINT, None)


if __name__ == "__main__":
    # self, host="localhost", port=5000, httpport=8000, connect_port: Tuple = None
    node = Server()
    node.loop()
