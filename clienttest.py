"""CD Chat client program"""
import logging
import sys
import selectors
import socket

import fcntl
import os

import signal

from datetime import datetime



class Client:
    """Chat Client process."""

    def __init__(self):
        """Initializes chat client."""
        self.sel = selectors.DefaultSelector()

        self._host = "localhost"
        self._port = 12363
        self._name = "Foo"
        self.clientChannel = "main"


        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sel.register(self.client_socket, selectors.EVENT_READ, self.read) 

        # REgistar o sinal de terminar par term o cliente
        signal.signal(signal.SIGINT, self.shutdown)
              

    def connect(self):
        """Connect to chat server and setup stdin flags."""
        try:
            self.client_socket.connect((self._host, self._port))
            self.client_socket.setblocking(False)

            # NOTE: Enviar a mensagemde registro para o server 😎
            # enivar o nome do cliente sem usar o protocolo
            self.client_socket.send(self._name.encode())

        
        except OSError as e:
            
            if e.errno == 106:
                print("Erro: Endereço já em uso.")
                self.sel.unregister(self.client_socket)
                self.client_socket.close()
            else:
                print("Erro que não connheço e ainda nao tratei", e.errno)
            sys.exit(1)



    def read(self, sock, mask):
        """Preciso ler as mensagens do servidor"""
        # soc
        data = sock.recv(1024)

        if data:
            print(f"msg recebida: {data}, {type(data)}")
            
        
        else:
            print('closing', sock) # NOTE: oserver foi fechado
            self.sel.unregister(sock)
            sock.close()
            
    def get_input(self, stdin, mask):
        message = stdin.read().rstrip('\n')


        if message.startswith("exit"):
            self.sel.unregister(self.client_socket)
            self.client_socket.close()
            print("Saiu do chat.")
            sys.exit(0)
        else:
            message = f"{self._name}: {message}"
            # message = f"{message}"
            self.client_socket.send(message.encode())



    def shutdown(self, signum, frame):
        """Terminar client em caso de um CTRL + C por exemplo."""
        print("Saiu do chat.")
        self.sel.unregister(self.client_socket)
        self.client_socket.close()
        sys.exit(0)


    def loop(self):
        """Loop indefinetely."""

        orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)

        self.sel.register(sys.stdin, selectors.EVENT_READ, self.get_input)
        
        while True:

            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)
