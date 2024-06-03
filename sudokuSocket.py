'''Sudoku node socket'''
import argparse
import selectors
import socket
import sys
import signal
import time
import threading
import queue
from collections import deque
import logging
import traceback
import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor

from sudokuHttp import sudokuHTTP
from sudokuHttp import CustomSudokuHTTP
from http.server import HTTPServer

from sudoku import Sudoku

import json

class Server:
    """Chat Server process."""

    def __init__(self, host="", port=5000, httpport=8000, connect_port: tuple = None, handicap: int = 1):        
        """Initialize server with host and port."""
        self.sel = selectors.DefaultSelector()
        
        self._host = host
        self._port = port
        self.connect_to = connect_port
        self.myip = self.get_my_ip()

        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Listen for incoming connections
        self.sock.bind((self._host, self._port))
        self.sock.listen(50)
        self.sock.setblocking(False)
        print(f"Listening on {self._host}:{self._port}")

        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)

        # http server
        self.http_server = HTTPServer(('localhost', httpport), lambda *args, **kwargs: CustomSudokuHTTP(self.sudoku_received, *args, **kwargs))

        # connection data
        self.connection: set = {self.sock}
        self.bind_connections: dict = {}
        self.ports: set = {}

        self.network = {f"{self.myip}:{self._port}": []}
        self.stats ={   
                        "all": {
                            "solved": 0, 
                            "validations": 0
                              },
                        "nodes": []
                      }

        # vars for messages and sudoku
        self.mySodokuGrid = Sudoku([])
        self.mySodokuQueue = queue.Queue()
        self.solution_found: bool = False
        self.positions: dict = {}
        self.checked: int = 0
        self.solved: int = 0 # how many sudokus were solved

        self.task_list = {} # peer: task

        # threading solved event
        self.solved_event = threading.Event()
        self.network_event = threading.Event()
        self.network_count = 0
        self.sudokuIds = {str: bool}
        self.current_sudoku_id = None

    def accept(self, sock, mask):
        """Accept incoming connections."""
        print("Server is accepting a new connection.")
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
            ip = self.myip
            # print(f"hostname: {hostname}, ip: {ip}")
            join_message = {"command":"join", "bindPoint": (self._host, self._port), "reply": send, "ip": ip}
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
                        ip = message['ip']
                        addr = (ip, int(port))
                        self.bind_connections[conn.getpeername()] = addr
                        self.ports[conn.getpeername()] = port

                        self.network[f"{self.myip}:{self._port}"].append(f"{ip}:{port}")

                        # send the list of bind connections values 
                        print(f"reply message: {message['reply']}")
                        if message['reply']:
                            bind_points = list(self.bind_connections.values())
                            join_reply = {"command": "join_reply", "bindPoints": bind_points, "ip": self.myip}
                            conn.send(json.dumps(join_reply).encode())

                        # imprime a lista de conexões atualizada
                        print(f'this node connections: {self.bind_connections}')

                    elif message['command'] == 'join_reply':
                        print(f'received points to connect: {message["bindPoints"]}')
                        
                        # update peer ip
                        ip = message['ip']
                        peer = self.bind_connections[conn.getpeername()]
                        self.bind_connections[conn.getpeername()] = (ip, peer[1])

                        self.network[f"{self.myip}:{self._port}"].append(f"{ip}:{peer[1]}")

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

                        task = self.mySodokuQueue.get()
                        solve = {"command": "solve", "sudoku": task}
                        conn.send(json.dumps(solve).encode())

                        self.task_list[conn.getpeername()] = task

                    elif message['command'] == 'network':
                        print(f"Recebido comando para enviar a rede")
                        my_network_list = [f"{connection[0]}:{connection[1]}" for connection in self.bind_connections.values()]
                        network = {"command": "update_network", "network": {f"{self.myip}:{self._port}": my_network_list}, "validations": self.checked, "solved": self.solved}
                        conn.send(json.dumps(network).encode())

                    elif message['command'] == 'update_network':
                        print(f"Recebido comando para atualizar a rede")
                        peer_network = message['network']
                        self.network.update(peer_network)
                        print(f"network updated")

                        # update the stats
                        validations = message['validations']
                        self.stats['all']['solved'] += message['solved']
                        self.stats['all']['validations'] += validations

                        address = list(message['network'].keys())[0] # get the address
                        node = {"address": address,
                                "validations": validations
                                }
                        self.stats['nodes'].append(node)

                        self.network_count += 1
                        if self.network_count == len(self.connection) - 1:
                            self.network_event.set()
                            self.network_count = 0

                    elif message['command'] == 'solve':
                        sudokuTask = message['sudoku']
                        checking_cell = tuple(sudokuTask[0])
                        r, c = checking_cell

                        puzzle = sudokuTask[1]
                        sudoku = Sudoku(puzzle)

                        # try to solve the sudoku
                        print(f"Resolvendo task ...")
                        result = sudoku.solve_sudoku()
                        
                        # update the checked count
                        self.checked += sudoku.get_check_count()
                        
                        print(f"Resolvido sudoku: {result}, checked: {self.checked}")
                        response = {"command": "solution", "sudoku": sudoku.get_sudoku(), "cell": checking_cell, "cell_value": sudoku.get_cell(r, c), "solution": result}
                        conn.send(json.dumps(response).encode())


                    elif message['command'] == 'solution':
                        print(f"lista de tarefas: {self.task_list}")
                        print(f"queue size: {self.mySodokuQueue.qsize()}")
                        
                        solved = message['solution']
                        print(f"Recebido solução: {solved}")

                        # remover o trabalho do nó
                        if conn.getpeername() in self.task_list:
                            self.task_list.pop(conn.getpeername())

                        if solved and not self.solution_found:
                            # atualizar o sudoku com a solução
                            self.mySodokuGrid.update_sudoku(message['sudoku'])
                            self.solution_found = True
                            self.sudokuIds[self.current_sudoku_id] = True
                            self.solved_event.set()

                            # TODO: depois enviar uma mensagem para os outros nodes 
                            # para pararem de tentar resolver o sudoku pois já foi resolvido

                        elif not solved and not self.mySodokuQueue.empty():

                            print(f"Enviando sudoku para resolver")
                            
                            task = self.mySodokuQueue.get()
                            solve = {"command": "solve", "sudoku": task}                            
                            conn.send(json.dumps(solve).encode())

                            self.task_list[conn.getpeername()] = task
                        elif self.mySodokuQueue.empty():
                            # ver se há mais de um nó a tentar resolver o sudoku
                            if len(self.task_list) > 1:
                                # pegar o trabalho do outro nó
                                task = self.task_list.popitem()[1]
                                solve = {"command": "solve", "sudoku": task}
                                conn.send(json.dumps(solve).encode())
                                self.task_list[conn.getpeername()] = task
                                print(f"Enviou task de outro nó")

                            elif len(self.task_list) == 1:
                                # get the task from the other node
                                task = self.task_list.popitem()[1]
                                task_puzzle = task[1]

                                # update the sudoku with the new puzzle
                                self.mySodokuGrid.update_sudoku(task_puzzle)

                                # generate new puzzles and add them to the queue
                                new_puzzles = self.mySodokuGrid.generate_puzzles()
                                for puzzle in new_puzzles:
                                    self.mySodokuQueue.put(puzzle)
                                
                                # send the new puzzles to the other nodes that aint working rn
                                for node in self.connection:
                                    if node != self.sock and node not in self.task_list.keys():
                                        task = self.mySodokuQueue.get()
                                        solve = {"command": "solve", "sudoku": task}
                                        node.send(json.dumps(solve).encode())
                                        self.task_list[node.getpeername()] = task

                                print(f"Enviou novas tarefas para os outros nodes")




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
        print(f"Recebido uma requisição")

        endpoint = sudoku
        match endpoint:
            case 'stats':
                print(f"Endpoint: /{endpoint}")
                self.stats['all']['solved'] = self.solved
                self.stats['all']['validations'] = self.checked
                self.stats['nodes'] = [{"address":f"{self.myip}:{self._port}", "validations": f"{self.checked}"}] 

                # if i'm alone
                if len(self.connection) == 1:
                    return self.stats

                for node in self.connection:
                    if node != self.sock:
                        stats = {"command": "network"}
                        node.send(json.dumps(stats).encode())

                # wait for the event to be set
                self.network_event.clear()
                self.network_event.wait()
                
                return self.stats

            case 'network':
                print(f"Endpoint: /{endpoint}")

                if len(self.connection) == 1:
                    return self.network

                # enviar mensagem para os outros nodes
                for node in self.connection:
                    if node != self.sock:
                        network = {"command": "network"}
                        node.send(json.dumps(network).encode())

                # update my network list
                my_network_list = [f"{connection[0]}:{connection[1]}" for connection in self.bind_connections.values()]
                self.network[f"{self.myip}:{self._port}"] = my_network_list

                self.network_event.clear()
                self.network_event.wait()

                return self.network
            
            case _:

                print(f"Endpoint: /solve")	
                sudokuToSolve = sudoku['sudoku']

                # gerar um id para o sudoku
                sudokuId = str(uuid.uuid4())
                self.current_sudoku_id = sudokuId
                self.sudokuIds[sudokuId] = False

                self.mySodokuGrid = Sudoku(sudokuToSolve)

                # # generate puzzles
                puzzles = self.mySodokuGrid.generate_puzzles()

                if puzzles is None:
                    print("Não há espaços vazios no sudoku")
                    return self.mySodokuGrid.grid

                # add the puzzle to the queue
                for puzzle in puzzles:
                    self.mySodokuQueue.put(puzzle)

                # enviar as primeiras mensagens para os outros nodes
                if len(self.connection) > 1:
                    for node in self.connection:
                        if node != self.sock:
                            solve = {"command": "askToSolve"}
                            node.send(json.dumps(solve).encode())
                
                start_time = time.time()
                print("Resolvendo sudoku...")

                # FIXME: criar um processo em uma thread para esse nó também participar da resolução
                pool = ThreadPoolExecutor(3)
                pool.submit(self.self_solve, sudokuId)

                print(f"Esperando resolução ... ")
                self.solved_event.clear() # clear the event
                self.solved_event.wait() # wait for the event to be set
                
                self.sudokuIds[sudokuId] = True
                     

                # clean the queue for this task dict
                self.mySodokuQueue = queue.Queue() 
                self.task_list.clear()

                # FIXME: reset variables tenho que resetar o evento também ?
                self.solution_found = False
                self.solved += 1
                print(f"Sudoku Resolvido\nTempo de execução: {time.time() - start_time} s")
                # return the solved sudoku
                return self.mySodokuGrid.grid


    def get_my_ip(self):
        """Get the ip address of the node"""
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip

   
    def self_solve(self, puzzle_id):
        """this node function to solve the sudoku"""

        # enquanto a solução não for encontrada
        while self.sudokuIds[puzzle_id] is False:
            # get a task from the queue if there is any
            if not self.mySodokuQueue.empty():
                task = self.mySodokuQueue.get()
  
            
            # add the task to the task list
            # self.task_list[self.sock.getpeername()] = task

            # start solving the sudoku
            puzzle = task[1]
            sudoku = Sudoku(puzzle)

            print(f"Self solving ...")
            solved = sudoku.solve_sudoku()

            # update the checked count
            self.checked += sudoku.get_check_count()

            print(f"Resolvido sudoku: {solved}, checked: {self.checked}, solution found: {self.solution_found}")
            if solved:
                # atualizar o sudoku com a solução
                self.mySodokuGrid.update_sudoku(sudoku.get_sudoku())
                self.solution_found = True
                self.solved_event.set()
                print(f"soltution found: {self.solution_found}")

                # update the sudokuid to true
                self.sudokuIds[puzzle_id] = True

                break
            elif self.solution_found or self.sudokuIds[puzzle_id]:
                # remove sudoku from the dict
                self.sudokuIds.pop(puzzle_id)
                break

        
        print(f"Self solve finished")

        return 
    
    
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

    parser = argparse.ArgumentParser(description="Sudoku node server")
    parser.add_argument("-p","--httpport", default=8000, type=int, help="HTTP port")
    parser.add_argument("-s","--socket", default=7000, type=int, help="P2P port")
    parser.add_argument("-a","--anchorage", default=None, help="Anchorage point")
    parser.add_argument("-H","--handicap", default=1, type=int, help="Check function delay")
    # print(f"args: {parser.parse_args()}")
    args = parser.parse_args()
    # print(f"args: {args}")

    http_port = args.httpport
    socket_port = args.socket
    anchorage = args.anchorage
    handicap = int(args.handicap)

    if anchorage is not None:
        host, port = tuple(anchorage.split(':'))
        anchorage = (host, int(port))
        # print(f"anchorage: {anchorage}")

    node = Server('', socket_port, http_port, anchorage, handicap)
    node.loop()
