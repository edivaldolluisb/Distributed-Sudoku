# Exemplo de rede P2P com 3 nós em Python usando sockets

import socket
import threading

# Configurações dos nós
nodes = [
    {"host": "localhost", "port": 5000},
    {"host": "localhost", "port": 5001},
    {"host": "localhost", "port": 5002}
]

def handle_connection(client_socket, node_id):
    while True:
        data = client_socket.recv(1024).decode("utf-8")
        if not data:
            break
        print(f"Node {node_id}: Recebido: {data}")
        # Aqui você pode processar os dados recebidos ou encaminhá-los para outros nós

def start_node(node_id):
    node = nodes[node_id]
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((node["host"], node["port"]))
    server_socket.listen(1)
    print(f"Node {node_id} escutando em {node['host']}:{node['port']}")

    while True:
        client_socket, _ = server_socket.accept()
        print(f"Node {node_id}: Nova conexão recebida")
        client_handler = threading.Thread(target=handle_connection, args=(client_socket, node_id))
        client_handler.start()

# Inicializa os nós
for i in range(len(nodes)):
    threading.Thread(target=start_node, args=(i,)).start()

'''

Exatamente! Do lado do servidor (nó), você não precisa explicitamente chamar `socket.connect()`. A função `socket.connect()` é usada apenas pelo cliente para estabelecer uma conexão com o servidor. No lado do servidor, você cria um socket, vincula-o a um endereço e porta e, em seguida, escuta por conexões entrantes.

Aqui está uma breve explicação:

1. **Cliente (Nó)**:
   - O cliente (nó) é aquele que inicia a conexão.
   - Ele cria um socket, chama `socket.connect()` para se conectar a um servidor (nó) específico e envia dados.
   - No exemplo que forneci anteriormente, não temos um cliente específico, pois todos os nós atuam como clientes e servidores ao mesmo tempo.

2. **Servidor (Nó)**:
   - O servidor (nó) é aquele que escuta por conexões entrantes.
   - Ele cria um socket, chama `socket.bind()` para vinculá-lo a um endereço e porta específicos e, em seguida, chama `socket.listen()` para começar a escutar por conexões.
   - Quando um cliente (nó) se conecta, o servidor aceita a conexão usando `socket.accept()` e inicia uma thread ou processo para lidar com essa conexão.

Portanto, no lado do servidor, você não precisa explicitamente chamar `socket.connect()`. A comunicação entre os nós ocorre quando um cliente se conecta ao servidor. 😊


'''


'''
Ótima pergunta! Vamos explorar como os peers podem se comunicar e como eles podem descobrir uns aos outros em uma rede P2P.

1. **Descoberta de Peers**:
   - Inicialmente, os peers precisam descobrir uns aos outros para estabelecer conexões.
   - Existem várias maneiras de fazer isso:
     - **Conhecimento Prévio**: Se você tiver uma lista fixa de peers conhecidos (por exemplo, de configurações ou arquivos de configuração), os peers podem se conectar diretamente a esses endereços.
     - **Bootstrap Nodes**: Alguns sistemas P2P usam "bootstrap nodes" (nós de inicialização). Esses nós são conhecidos e estão sempre disponíveis. Os peers se conectam a esses nós primeiro e obtêm informações sobre outros peers.
     - **Broadcast ou Multicast**: Os peers podem enviar mensagens de broadcast ou multicast para anunciar sua presença. Outros peers que ouvirem essas mensagens podem responder e estabelecer conexões.
     - **DHT (Tabela de Hash Distribuída)**: Alguns sistemas P2P usam DHTs para armazenar informações sobre peers. Cada peer tem uma chave (geralmente baseada em algum identificador único) e pode procurar outros peers usando essa chave.

2. **Monitoramento de Peer**:
   - Para saber se um peer "morreu", outros peers podem usar técnicas como:
     - **Timeouts**: Se um peer não responder após um certo período de tempo, outros peers podem considerá-lo inativo ou morto.
     - **Ping/Keep-Alive**: Os peers podem enviar mensagens periódicas (ping ou keep-alive) para verificar se o outro peer ainda está ativo.
     - **Verificação de Conteúdo**: Alguns sistemas P2P verificam se os peers estão compartilhando conteúdo válido. Se um peer não estiver contribuindo com dados úteis, ele pode ser considerado inativo.

3. **Redundância**:
   - Para garantir a robustez da rede, os peers geralmente se conectam a vários outros peers (não apenas um).
   - Se um peer falhar, outros ainda podem se comunicar com os peers restantes.

Lembre-se de que a implementação real pode variar dependendo do sistema P2P específico. Alguns sistemas, como o BitTorrent, usam uma combinação dessas técnicas. Espero que isso esclareça como os peers se comunicam e como eles podem detectar se um peer está inativo! 😊'''

# exemplo de uma mensagem de monitoramento de peer por timeout
import time

class Peer:
    def __init__(self, address):
        self.address = address
        self.last_activity = time.time()

    def update_activity(self):
        self.last_activity = time.time()

    def is_active(self, timeout=60):
        return time.time() - self.last_activity < timeout

# Exemplo de uso
peer1 = Peer("192.168.1.10")
peer2 = Peer("192.168.1.20")

# Atualize a atividade dos peers (chamado quando receber dados de um peer)
peer1.update_activity()

# Verifique se um peer está ativo
if peer2.is_active():
    print("Peer 2 está ativo.")
else:
    print("Peer 2 está inativo ou morto.")
