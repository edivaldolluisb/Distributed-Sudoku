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
        self.sock.setblocking(False)

        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)

        # http server
        self.http_server = HTTPServer(('localhost', httpport), lambda *args, **kwargs: CustomSudokuHTTP(self.sudoku_received, *args, **kwargs))

        # connection data
        self.connection = []
  


    def accept(self, sock, mask):
        conn, addr = sock.accept()  # Should be ready
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)

        print(f'got a connectio ffrom {conn}')
        conn.send


    def connect(self):
        """Connect to a peer"""
        try:
            connection = socket.create_connection(self.connect_to)
            self.connection.append(connection)

            print(f'connected to :{connection}')

            # send a wellcome message to the other node

        except:
            print('problema ao conectar!')



    def read(self, conn, mask):

        try:
            data = conn.recv(1024)

            if data:
                print(data)

                
            else:
                print(f'closing connection for:{conn.getpeername()}')

                self.sel.unregister(conn)
                conn.close()
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

        self.sel.unregister(self.sock)
        self.sock.close()
        self.http_server.server_close() # fechar o servidor http
        print("Server fechado.")
        sys.exit(0)   


    def listen(self):
        """Listen for incoming connections."""
        self.sock.bind((self._host, self._port))
        self.sock.listen(50)
        print(f"Listening on {self._host}:{self._port}")


    def loop(self):
        """Loop indefinetely."""
        listener_thread = threading.Thread(target=self.listen)
        listener_thread.start()

        if self.connect_to is not None:
            time.sleep(2)
            self.connect()

        try:
            print('Sudoku server running ...')
            server_http_thread = threading.Thread(target=self.http_server.serve_forever)
            server_http_thread.start()

            while True:
                events = self.sel.select()
                for key, mask in events:
                    callback = key.data
                    callback(key.fileobj, mask)
        
        except KeyboardInterrupt:
            self.shutdown(signal.SIGINT, None)


if __name__ == "__main__":
    # self, host="localhost", port=5000, httpport=8000, connect_port: Tuple = None
    node = Server()
    node.loop()
