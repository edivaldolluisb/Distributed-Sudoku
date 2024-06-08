'''Sudoku node socket'''
import argparse
import selectors
import socket
import sys, platform, signal, os
import time
import threading
import queue
from collections import deque
import logging
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

from http.server import HTTPServer
from HttpServer import sudokuHTTP

from sudoku import Sudoku

import json, pickle

# logging config 
logging.basicConfig(filename=f"{sys.argv[0]}.log", level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Server:
    """Chat Server process."""

    def __init__(self, host="", port=5000, httpport=8000, connect_port: tuple = None, handicap: int = 1):        
        """Initialize server with host and port."""
        self.sel = selectors.DefaultSelector()
        
        self._host = host
        self._port = port
        self._http_port = httpport
        self._handicap = handicap * 0.001 # 0.001
        self.connect_to = connect_port
        self.myip = self.get_my_ip()

        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Listen for incoming connections
        self.sock.bind((self._host, self._port))
        self.sock.listen(50)
        self.sock.setblocking(False)
        print(f"Listening on {self.myip}:{self._port}")

        self.sel.register(self.sock, selectors.EVENT_READ, self.accept)

        # http server
        self.http_server = HTTPServer(('localhost', httpport), lambda *args, **kwargs: sudokuHTTP(self.sudoku_received, *args, **kwargs))

        # connection data
        self.connection: set = set()
        self.bind_connections: dict = {}

        self.network = {f"{self.myip}:{self._port}": []}
        self.stats = {  "solved": 0, 
                        "validations": 0}
                      

        # vars for messages and sudoku
        self.mySodokuGrid = Sudoku([])
        self.mySodokuQueue = queue.Queue()
        self.solution_found: bool = True
        self.checked: int = 0
        self.solved: int = 0 # how many sudokus were solved
        self.network_cache = {}
        self.keep_alive_nodes = {}
        self.task_list = {} # peer: task
        self.sudoku_cache = {} # cache for the sudoku


        # threading solved event
        self.solved_event = threading.Event()
        self.network_event = threading.Event()
        self.network_count = 0
        self.sudokuIds = {str: bool}
        self.current_sudoku_id = None
        self.pool = ThreadPoolExecutor(20)

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

            # send my join message
            ip = self.myip
            # print(f"hostname: {hostname}, ip: {ip}")
            join_message = {"command":"join", "bindPoint": (self.myip, self._port), "reply": send, "ip": ip}
            connection.sendall(json.dumps(join_message).encode())

            logging.info(f"{self.myip}:{self._port} connected to {self.connect_to}")

        except Exception as e:
            print(f'problema ao conectar!. Error : {e}')

    def read(self, conn, mask):
        """Read incomming messages"""
        try:
            data = conn.recv(1024)

            if data:
                try:
                    message = json.loads(data.decode())
                    print(f'received message: {message}')

                    self.keep_alive_nodes[conn] = True # set connection to true

                    if message['command'] == 'join':
                        # add the connection to the bind connections
                        host, port = message['bindPoint']
                        ip = message['ip']
                        addr = (ip, int(port))
                        self.bind_connections[conn.getpeername()] = addr

                        peer_address = f"{ip}:{port}"

                        self.network[f"{self.myip}:{self._port}"].append(peer_address)

                        # verificar se seus dados em cache
                        peer_data = self.network_cache.get(peer_address)

                        # send the list of bind connections values 
                        print(f"reply message: {message['reply']}")
                        if message['reply']:
                            copy_connections = self.bind_connections.copy()
                            # remove the connection that is sending the message
                            copy_connections.pop(conn.getpeername())
                            bind_points = list(copy_connections.values())
                            join_reply = {"command": "join_reply", 
                                          "bindPoints": bind_points, 
                                          "ip": self.myip,
                                          "data": peer_data}
                            
                            conn.send(json.dumps(join_reply).encode())

                        # imprime a lista de conexões atualizada
                        print(f'this node connections: {self.bind_connections}')

                        self.pool.submit(self.send_solve_on_join, conn)
                
                        logging.info(f"{self.myip}:{self._port} connected to {addr}")

                    elif message['command'] == 'join_reply':
                        print(f'received points to connect: {message["bindPoints"]}')

                        # verificar se há dados no cache
                        if message['data'] is not None:
                            print(f"updating cache with: {message['data']}")
                            self.solved = message['data']['solved']
                            self.checked = message['data']['validations']

                        
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
                            if node not in self.bind_connections.values() :

                                self.connect_to = node
                                self.connect(False)

                        logging.info(f"{self.myip}:{self._port} received nodes list: {message['bindPoints']}")

                    elif message['command'] == 'askToSolve':
                        print(f"Recebido comando de resolução de sudoku: {message}")
                        print(f"Asking for sudoku to solve")
                        solve = {"command": "agToSolve"}
                        conn.send(json.dumps(solve).encode())
                    
                    elif message['command'] == 'agToSolve':
                        print(f"Recebido comando de confirmação para resolver")
                        print(f"enviando sudoku para resolver")

                        # ver se tem tarefas na fila
                        if not self.mySodokuQueue.empty:
                            task = self.mySodokuQueue.get()
                            solve = {"command": "solve", "sudoku": task, "sudokuId": self.current_sudoku_id, "cache": self.mySodokuGrid.grid}
                            conn.send(json.dumps(solve).encode())

                            self.task_list[conn.getpeername()] = task
                        
                        elif len(self.task_list) > 0:
                            # pegar o trabalho do outro nó
                            task = self.task_list.popitem()[1]
                            solve = {"command": "solve", "sudoku": task, "sudokuId": self.current_sudoku_id, "cache": self.mySodokuGrid.grid}
                            conn.send(json.dumps(solve).encode())
                            self.task_list[conn.getpeername()] = task
                            print(f"Enviou task de outro nó")


                    elif message['command'] == 'network':
                        print(f"Recebido comando para enviar a rede")
                        my_network_list = [f"{connection[0]}:{connection[1]}" for connection in self.bind_connections.values()]
                        network = {"command": "update_network", "network": {f"{self.myip}:{self._port}": my_network_list}, "validations": self.checked}
                        conn.send(json.dumps(network).encode())

                    elif message['command'] == 'update_network':
                        print(f"Recebido comando para atualizar a rede")
                        peer_network = message['network']
                        self.network.update(peer_network)
                        print(f"network updated")


                        self.network_count += 1
                        if self.network_count == len(self.connection):
                            self.network_event.set()
                            self.network_count = 0

                    elif message['command'] == 'solve':
                        check_cache = message['cache']
                        # check if the sudoku is in the cache
                        check_cache = pickle.dumps(check_cache)
                        if check_cache in self.sudoku_cache:
                            print(f"Enviando sudoku salvo em cache")
                            response = {"command": "solution", "sudoku": self.sudoku_cache[check_cache], "sudokuId": message['sudokuId'], "solution": True}
                            conn.send(json.dumps(response).encode())
                            return

                        # store the sudoku id
                        sudoku_id = message['sudokuId']
                        self.sudokuIds[sudoku_id] = False

                        # resolver em uma thread
                        self.pool.submit(self.solve_sudoku, message, conn)


                    elif message['command'] == 'solution':
                        # print(f"Task list: {self.task_list}, queue: {list(self.mySodokuQueue.queue), self.mySodokuQueue.qsize()}")

                        
                        solved = message['solution']
                        solvedId = message['sudokuId']
                        print(f"Recebido solução: {solved} found {self.solution_found}")



                        # remover o trabalho do nó
                        if conn.getpeername() in self.task_list:
                            self.task_list.pop(conn.getpeername())

                        if solved and not self.solution_found and self.sudokuIds.get(solvedId) is False or self.solved_event.is_set() is False:
                            # atualizar o sudoku com a solução
                            self.mySodokuGrid.update_sudoku(message['sudoku'])
                            self.solution_found = True
                            self.sudokuIds[self.current_sudoku_id] = True
                            self.solved_event.set()


                        elif not solved and not self.mySodokuQueue.empty():

                            print(f"Enviando sudoku para resolver")
                            
                            task = self.mySodokuQueue.get()
                            solve = {"command": "solve", "sudoku": task, "sudokuId": self.current_sudoku_id, "cache": self.mySodokuGrid.grid}                            
                            conn.send(json.dumps(solve).encode())

                            self.task_list[conn.getpeername()] = task
                        elif self.mySodokuQueue.empty():
                            # ver se há mais de um nó a tentar resolver o sudoku
                            if len(self.task_list) > 1:
                                # pegar o trabalho do outro nó
                                task = self.task_list.popitem()[1]
                                solve = {"command": "solve", "sudoku": task, "sudokuId": self.current_sudoku_id, "cache": self.mySodokuGrid.grid}
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
                                    if node not in self.task_list.keys():
                                        task = self.mySodokuQueue.get()
                                        solve = {"command": "solve", "sudoku": task, "sudokuId": self.current_sudoku_id, "cache": self.mySodokuGrid.grid}
                                        node.send(json.dumps(solve).encode())
                                        self.task_list[node.getpeername()] = task

                                print(f"Enviou novas tarefas para os outros nodes")


                    elif message['command'] == 'stop':
                        # parar a resolução do sudoku
                        ID = message['sudokuId']
                        if ID in self.sudokuIds:
                            self.sudokuIds.pop(ID)

                    elif message['command'] == 'keep_alive':
                        IP = message['IP']
                        IP_status = message['status']
                        self.network_cache[IP] = IP_status

                        # send reply
                        reply_message = {"command": "keep_alive_reply"}
                        send_message = json.dumps(reply_message).encode()
                        conn.send(send_message)
                    
                    elif message['command'] == 'keep_alive_reply':
                        # set connection to true
                        self.keep_alive_nodes[conn] = True


                except json.JSONDecodeError as e:
                    print(f"Erro ao decodificar a mensagem JSON enviada por {conn}: {e}")
                    # self.shutdown(signal.SIGINT, None)

            else:
                print(f'closing connection for:{conn.getpeername()}')
                self.close_connection(conn)

        except ConnectionResetError:
            print(f'conexão fechada abrumtamente por {conn.getpeername()}')
            self.close_connection(conn)

        except Exception as e:
            print(f'Erro ao ler os dados: {e}')
            # traceback.print_exc(e)
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            # print(exc_type, fname, exc_tb.tb_lineno)
            # self.shutdown(signal.SIGINT, None)

    def sudoku_received(self, sudoku):
        """processar o sudoku recibido por http"""
        print(f"Recebido uma requisição")

        endpoint = sudoku
        match endpoint:
            case 'stats':
                print(f"Endpoint: /{endpoint}")
                return_status ={   
                        "all": {
                            "solved": 0, 
                            "validations": 0
                              },
                        "nodes": []
                      }

                nodes = [{"address":f"{self.myip}:{self._port}",
                          "validations": self.checked}]
                return_status['all']['solved'] += self.solved
                return_status['all']['validations'] += self.checked
                
                for address, value in self.network_cache.items():
                    solved = value["solved"]
                    checked =  value["validations"]
                    print(checked, solved)
                    return_status['all']['solved'] += solved
                    return_status['all']['validations'] += checked

                    host, port = address.split(':')
                    node = (host, int(port))
                    if node not in self.bind_connections.values():
                        continue
                    node = {"address": address, "validations": checked}
                    nodes.append(node)

                return_status['nodes'] = nodes
                
                return return_status

            case 'network':
                print(f"Endpoint: /{endpoint}")

                if len(self.connection) == 0:
                    return self.network

                # enviar mensagem para os outros nodes
                for node in self.connection:
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
                self.solution_found = False # procurando solução

                # gerar um id para o sudoku
                sudokuId = str(uuid.uuid4())
                self.current_sudoku_id = sudokuId
                self.sudokuIds[sudokuId] = False
                self.mySodokuGrid = Sudoku(sudokuToSolve, base_delay=self._handicap)

                check_cache = pickle.dumps(sudokuToSolve)
                # check_cache = str(sudokuToSolve)
                # verificar se o sudoku já foi resolvido
                if check_cache not in self.sudoku_cache:
                    self.sudoku_cache[check_cache] = []
                else:
                    print("Sudoku salvo em cache")
                    self.solved += 1
                    self.sudokuIds.pop(sudokuId)

                    return self.sudoku_cache[check_cache]

                # # generate puzzles
                puzzles = self.mySodokuGrid.generate_puzzles()

                if puzzles is None:
                    print("Não há espaços vazios no sudoku")
                    return self.mySodokuGrid.grid

                # add the puzzle to the queue
                for puzzle in puzzles:
                    self.mySodokuQueue.put(puzzle)

                # enviar as primeiras mensagens para os outros nodes
                print(len(self.connection))
                if len(self.connection) > 0:
                    for node in self.connection:
                        solve = {"command": "askToSolve"}
                        node.send(json.dumps(solve).encode())
                
                start_time = time.time()
                print("Resolvendo sudoku...")

                # FIXME: criar um processo em uma thread para esse nó também participar da resolução
                # pool = ThreadPoolExecutor(3)
                self.pool.submit(self.self_solve, sudokuId)

                print(f"Esperando resolução ... ")
                self.solved_event.clear() # clear the event
                self.solved_event.wait() # wait for the event to be set

                # enviar stop message para os outros nodes
                for node in self.connection:
                    stop = {"command": "stop", "sudokuId": self.current_sudoku_id}
                    node.send(json.dumps(stop).encode())

                # adiocioar o sudoku ao cache
                self.sudoku_cache[check_cache] = self.mySodokuGrid.grid
                     

                # clean the queue for this task dict
                self.mySodokuQueue = queue.Queue() 
                self.task_list.clear()

                # resetar as variáveis              
                self.sudokuIds.pop(sudokuId)
                self.current_sudoku_id = None
                self.solution_found = True
                self.solved += 1
                print(f"Sudoku Resolvido\nTempo de execução: {time.time() - start_time} s")
                # return the solved sudoku
                return self.mySodokuGrid.grid


    def get_my_ip(self):
        """Get the ip address of the node"""

        # chekc my os system 
        if platform.system() == "Windows":
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip
        else:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()

            return ip

   
    def self_solve(self, puzzle_id):
        """this node function to solve the sudoku"""

        # enquanto a solução não for encontrada
        while self.sudokuIds.get(puzzle_id) is False:
            # get a task from the queue if there is any
            if not self.mySodokuQueue.empty():
                task = self.mySodokuQueue.get()
            
            elif len(self.task_list) > 0:
                # pegar task na lista de tarefas
                task = self.task_list.popitem()[1]
                print(f"Peguei na lista de tarefas")
  
            
            # add the task to the task list
            self.task_list['self.socket'] = task
            # print(f"Task list: {self.task_list}, queue: {list(self.mySodokuQueue.queue), self.mySodokuQueue.qsize()}")

            # start solving the sudoku
            puzzle = task[1]
            sudoku = Sudoku(puzzle, base_delay=self._handicap)

            print(f"Self solving ...")
            solved = sudoku.solve_sudoku()

            # update the checked count
            self.checked += sudoku.get_check_count()
            solution = self.sudokuIds.get(puzzle_id)
            print(f"Self solution found: {solved}, checked: {self.checked}, puzzle solved: {solution}")
            if solved and self.sudokuIds.get(puzzle_id) is False:
                # atualizar o sudoku com a solução
                self.mySodokuGrid.update_sudoku(sudoku.get_sudoku())
                self.solved_event.set()
                print(f"soltution found: {self.solution_found}")

                # update the sudokuid to true
                self.sudokuIds[puzzle_id] = True

                break

            elif solution is True or solution is None:
                break
            

        
        print(f"Self solve finished!")
        return 
    

    def solve_sudoku(self, message, conn):
        """solve sudoku
        Args:
            message (dict): message received
            conn (socket): connection who sent the message
        """
        sudokuTask = message['sudoku']
        ID = message['sudokuId']
        checking_cell = tuple(sudokuTask[0])

        puzzle = sudokuTask[1]
        sudoku = Sudoku(puzzle, base_delay=self._handicap)

        # try to solve the sudoku
        print(f"Resolvendo task ...")
        result = sudoku.solve_sudoku()
        
        # update the checked count
        self.checked += sudoku.get_check_count()
        
        # Send message to the node if wasn't solved yet
        if self.sudokuIds.get(ID) is not None:
            print(f"Resolvido sudoku: {result}, checked: {self.checked}")
            response = {"command": "solution", "sudoku": sudoku.get_sudoku(), "sudokuId": ID, "solution": result}
            conn.send(json.dumps(response).encode())
        else:
            print("Thread terminada!")
        
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

    def keep_alive(self):
        """Enviar uma mensagem periodica aos nodes para verificar se ainda estão conectados"""

        while True: 
            
            # skip if im alone
            if len(self.connection) == 0:
                time.sleep(5)
                continue

            print("Checking bros ...")
            for conn in self.connection:
                if conn != self.sock:
                    message = {"command": "keep_alive",
                               "status": {
                                    "solved": self.solved, 
                                    "validations": self.checked
                                },
                                 "IP": f"{self.myip}:{self._port}"
                              }
                    conn.send(json.dumps(message).encode())

                    self.keep_alive_nodes[conn] = False
                   

            time.sleep(3)
            # # check if the connection is still alive
            for node, value in self.keep_alive_nodes.items():
                if value is False:
                    print(f"Conexão perdida com {node}")
                    # remove it from the network
                    peer = self.bind_connections[node.getpeername()]
                    self.network.pop(f"{peer[0]}:{peer[1]}")

                    self.close_connection(node)

    def send_solve_on_join(self, conn):
        # ver se estou a resolver um puzzle no momento 
        time.sleep(0.5) # FIXME: verificar a abordagem de tempo
        if not self.solution_found or not self.solved_event.is_set():
            if not self.mySodokuQueue.empty():
                task = self.mySodokuQueue.get()
                solve = {"command": "solve", "sudoku": task, "sudokuId": self.current_sudoku_id, "cache": self.mySodokuGrid.grid}
                conn.send(json.dumps(solve).encode())
                self.task_list[conn.getpeername()] = task
                print(f"Enviou sudoku para resolver")
            elif len(self.task_list) > 0:
                # pegar o trabalho do outro nó
                task = self.task_list.popitem()[1]
                solve = {"command": "solve", "sudoku": task, "sudokuId": self.current_sudoku_id, "cache": self.mySodokuGrid.grid}
                conn.send(json.dumps(solve).encode())
                self.task_list[conn.getpeername()] = task
                print(f"Enviou task de outro nó")


    def close_connection(self, conn):
        """Close the connection."""
        print(f'Closing connection for {self.bind_connections[conn.getpeername()]} ')
        if conn in self.connection:
            if conn in self.sel.get_map(): # check if socket is registered
                self.sel.unregister(conn)
            self.connection.remove(conn)
            self.bind_connections.pop(conn.getpeername())
            print('Connection closed for node')
            conn.close()

    def loop(self):
        """Loop indefinetely."""
        logging.info(f"Server is running on {self._host}:{self._port} http port: {self._http_port}")

        # send keep alive message
        self.pool.submit(self.keep_alive)

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
        finally:
            logging.info(f"Server {self.myip}:{self._host} is shutting down.")

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

