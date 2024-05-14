'''Sudoku node socket'''
import selectors
import socket
import sys
import signal

import threading

from sudokuHttp import sudokuHTTP
from sudokuHttp import CustomSudokuHTTP
from http.server import HTTPServer

from sudoku import Sudoku

class Server:
    """Chat Server process."""

    def __init__(self):
        """Initialize server with host and port."""
        self.sel = selectors.DefaultSelector()
        
        self._host = "localhost"
        self._port = 12363


        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self._host, self._port))
        self.sock.listen(50)
        self.sock.setblocking(False)

        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)

        # http server
        self.http_server = HTTPServer(('localhost', 8080), lambda *args, **kwargs: CustomSudokuHTTP(self.sudoku_received, *args, **kwargs))
  


    def accept(self, sock, mask):
        conn, addr = sock.accept()  # Should be ready
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)



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


    def loop(self):
        """Loop indefinetely."""
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
    server = Server()
    server.loop()