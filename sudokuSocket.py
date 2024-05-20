'''Sudoku node socket'''
import selectors
import socket
import sys
import signal
import time
import threading
import queue
import pprint

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
        self.ports={}

        # queues for messages and sudoku
        self.mySodokuGrid = Sudoku([])
        self.mySodokuQueue = queue.Queue()

    def accept(self, sock, mask):
        """Accept incoming connections."""
        print("Server is accepting.")
        conn, addr = sock.accept()  # Should be ready
        conn.setblocking(False)
        self.sel.register(conn, selectors.EVENT_READ, self.read)
        self.connection.add(conn)
        

        print(f'this node got a new connection')

    def connect(self, send: bool = True):
        """Connect to a peer"""
        try:
            connection = socket.create_connection(self.connect_to)
            self.connection.add(connection)

            print(f'this node connected to :{connection.getpeername()}')
            connection.setblocking(False)
            self.sel.register(connection, selectors.EVENT_READ, self.read)

            # create a bind point in the bind connections variable
            self.bind_connections[connection.getpeername()] = connection.getpeername()
            self.ports[connection.getpeername()] = self.connect_to[1]

            # send my join message
            join_message = {"command":"join", "bindPoint": (self._host, self._port), "reply": send}
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
                    print(f'received message: {message}')

                    if message['command'] == 'join':
                        # add the connection to the bind connections
                        host, port = message['bindPoint']
                        addr = (host, int(port))
                        self.bind_connections[conn.getpeername()] = addr
                        self.ports[conn.getpeername()] = port

                        # send the list of bind connections values 
                        print(f"reply message: {message['reply']}")
                        if message['reply']:
                            bind_points = list(self.bind_connections.values())
                            join_reply = {"command": "join_reply", "bindPoints": bind_points}
                            conn.send(json.dumps(join_reply).encode())

                        # imprime a lista de conexões atualizada
                        print(f'this node connections: {self.bind_connections}')

                    elif message['command'] == 'join_reply':
                        print(f'received points to connect: {message["bindPoints"]}')

                        # connect to the other nodes
                        for node in message['bindPoints']:
                            node = tuple(node)
                            print(f'node: {node}')
                            print(f'my connections: {self.bind_connections}')
                            # check if hasn't connected to the node and port yet
                            if node not in self.bind_connections.values() and node[1] != self._port and node[1] not in self.ports.values():
                            # if node not in self.bind_connections.values() and node[1] != self._port:
                                self.connect_to = node
                                self.connect(False)

                    elif message['command'] == 'askToSolve':
                        print(f"Recebido comando de resolução de sudoku: {message}")
                        print(f"Asking for sudoku to solve")
                        solve = {"command": "agToSolve"}
                        conn.send(json.dumps(solve).encode())
                    
                    elif message['command'] == 'agToSolve':
                        print(f"Recebido comando de confirmação para resolver")
                        print(f"enviando sudoku para resolver")

                        print(list(self.mySodokuQueue.queue))
                        solve = {"command": "solve", "sudoku": (self.mySodokuQueue.get(), self.mySodokuGrid.grid)}
                        conn.send(json.dumps(solve).encode())

                    elif message['command'] == 'solve':
                        print(f"Resolvendo: {message['sudoku']}")
                        sudokuTask = message['sudoku'][1]
                        line = message['sudoku'][0]

                        solving = Sudoku(sudokuTask).solve_line(sudokuTask ,line, 0)
                        
                        # time.sleep(1)
                        print(f"Resolvido sudoku: {sudokuTask[line]}")
                        response = {"command": "solved", "sudoku": (line, sudokuTask[line])}
                        conn.send(json.dumps(response).encode())


                    elif message['command'] == 'solved':
                        print(f"Recebido linha resolvida: {message['sudoku']}")
                        solved_line = message['sudoku']
                        self.mySodokuGrid.update_row(int(solved_line[0]), solved_line[1])
                        
                        # check if there is remaning tasks to solve
                        if not self.mySodokuQueue.empty():
                            print(f"Enviando sudoku para resolver")
                            print(list(self.mySodokuQueue.queue))
                            solve = {"command": "solve", "sudoku": (self.mySodokuQueue.get(), self.mySodokuGrid.grid)}
                            conn.send(json.dumps(solve).encode())


                except json.JSONDecodeError as e:
                    print(f"Erro ao decodificar a mensagem JSON: {e}")
                    self.shutdown(signal.SIGINT, None)

            else:
                print(f'closing connection for:{conn.getpeername()}')

                self.sel.unregister(conn)
                conn.close()
                self.connection.remove(conn)
                self.bind_connections.pop(conn.getpeername())


        except ConnectionResetError:
            print(f'conexão fechada abrumtamente por {conn.getpeername()}')
            self.sel.unregister(conn)
            self.bind_connections.pop(conn.getpeername())
            print(f'this node connections: {self.bind_connections}')
            self.connection.remove(conn)
            conn.close()

        except Exception as e:
            print(f'Erro ao ler os dados: {e}')
            self.shutdown(signal.SIGINT, None)
            sys.exit(1)

    def sudoku_received(self, sudoku):
        """processar o sudoku recibido por http"""
        print(f"Recebido sudoku: {sudoku} server")
        sudokuToSolve = sudoku['sudoku']
        self.mySodokuGrid = Sudoku(sudokuToSolve)
        
        for i in range(3):
            
            self.mySodokuQueue.put(i)

        if len(self.connection) > 1:
            for node in self.connection:
                if node != self.sock:
                    solve = {"command": "askToSolve"}
                    node.send(json.dumps(solve).encode())
        
        start_time = time.time()
        while not self.mySodokuGrid.is_complete():
            # print(f"Esperando resolução... {self.mySodokuQueue.qsize()}")
            # print(len(self.connection))
            time.sleep(1)
            

        # self.mySodokuGrid.solve_sudoku(self.mySodokuGrid.grid)
        # self.solve_sudoku(self.mySodokuGrid.grid)
        

        # clean the queue for this task and
        self.mySodokuQueue = queue.Queue() 
        print(f"Tempo de execução: {time.time() - start_time}")
        # return the solved sudoku
        return self.mySodokuGrid.grid
    

    def solve_sudoku(self, puzzle):
        sudoku = Sudoku(puzzle)
        if sudoku.check():
            return True
        
        row, col = self.mySodokuGrid.find_next_empty(puzzle)

        # if row is None:
        #     return True

        for guess in range(1, 10):      

            if self.mySodokuGrid.is_valid(puzzle, guess, row, col):
                puzzle[row][col] = guess

                if self.solve_sudoku(puzzle):
                    # print('achou', guess, row, col)
                    # send a message to the other nodes
                    for node in self.connection:
                        if node != self.sock:
                            solve = {"command": "msg", "sudoku": (row, puzzle)}
                            node.send(json.dumps(solve).encode())
                            time.sleep(0.5)
                    return True

            puzzle[row][col] = 0

        return False 


    def shutdown(self, signum, frame):
        """Shutdown server."""

        print("Server is shutting down.")
        # fechar conexões com outros nodes
        for conn in self.connection:
            self.sel.unregister(conn)
            conn.close()

        self.http_server.server_close() # fechar o servidor http
        print("Server fechado.")
        sys.exit(0)


    def loop(self):
        """Loop indefinetely."""

        # connect to another node
        if self.connect_to is not None:
            # time.sleep(1)
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
