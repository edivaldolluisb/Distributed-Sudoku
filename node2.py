# sudoku_node.py (Nó Sudoku)

import socket
import threading

class SudokuNode:
    def __init__(self, node_id, http_port, socket_port):
        self.node_id = node_id
        self.http_port = http_port
        self.socket_port = socket_port
        self.sudoku_data = {}  # Dados do Sudoku resolvidos

    def handle_client(self, client_socket):
        # Lógica para lidar com conexões de clientes via socket
        pass

    def start_http_server(self):
        # Inicie um servidor HTTP na porta self.http_port
        pass

    def start_socket_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(("0.0.0.0", self.socket_port))
        server_socket.listen(5)

        print(f"Nó {self.node_id} ouvindo na porta {self.socket_port}")

        while True:
            client_socket, _ = server_socket.accept()
            client_handler = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_handler.start()

if __name__ == "__main__":
    node1 = SudokuNode(node_id=1, http_port=8081, socket_port=9001)
    node2 = SudokuNode(node_id=2, http_port=8082, socket_port=9002)

    # Inicie os servidores HTTP e de socket em threads separadas
    threading.Thread(target=node1.start_http_server).start()
    threading.Thread(target=node1.start_socket_server).start()

    threading.Thread(target=node2.start_http_server).start()
    threading.Thread(target=node2.start_socket_server).start()
