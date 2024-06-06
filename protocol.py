"""Protocol for node - Computação Distribuida Final Project"""
import json
from datetime import datetime
from socket import socket


class Message:
    """Message Type."""

    def __init__(self, command):
        """Initialize message with command, os comando vão ser passados depois"""
        self.command = command
        self._timestamp = int(datetime.now().timestamp()) 
        self._msg = None


    def toJson(self, dict: dict):
        self._msg = json.dumps(dict)


    @property
    def timestamp(self) -> datetime:
        """Retrieve message timestamp."""
        return self._timestamp
    

    def __str__(self):
        return self._msg


    
class JoinMessage(Message):
    """Message to join a chat channel."""
    def __init__(self, channel):
        super().__init__("join")
        self.channel = channel

        # fzr a convertion para json
        msg = {
            "command": self.command,
            "channel": self.channel
        }
        self.toJson(msg)


    def __str__(self):
        return self._msg
    


class RegisterMessage(Message):
    """Message to register username in the server."""
    def __init__(self, user):
        super().__init__("register")
        self.user = user
    
        msg ={
            "command": self.command,
            "user": self.user
        }
        self.toJson(msg)

    
    def __str__(self):
        return self._msg
        
    
class TextMessage(Message):
    """Message to chat with other clients."""

    def __init__(self, message, channel , ts: datetime = None):
        super().__init__("message")
        self.message = message
        self.channel = channel
        self.ts = super().timestamp

        if channel == None:
            msg = {
                "command": self.command,
                "message": self.message,
                "ts": self.ts
            }
        else:
            msg = {
                "command": self.command,
                "message": self.message,
                "channel": self.channel,
                "ts": self.ts
            }

        self.toJson(msg)
        # print(self._msg)
    
    
    def __str__(self):
        return self._msg
    

class CDProto:
    """Computação Distribuida Protocol."""

    @classmethod
    def register(cls, username: str) -> RegisterMessage:
        """Creates a RegisterMessage object."""
        return RegisterMessage(username)

    @classmethod
    def join(cls, channel: str) -> JoinMessage:
        """Creates a JoinMessage object."""
        return JoinMessage(channel)

    @classmethod
    def message(cls, message: str, channel: str = None) -> TextMessage:
        """Creates a TextMessage object."""
        return TextMessage(message, channel)

    @classmethod
    def send_msg(cls, connection: socket, msg: Message):
        """Sends through a connection a Message object."""

        convertedMsg = msg.__str__().encode('utf-8')
        msgLen = len(convertedMsg)  # NOTE: definir o tamanho da mensagem
        
        header = msgLen.to_bytes(2, byteorder="big")
        try:
            # tentar enviar a mensagem
            # NOTE: o send all é para garantir que a mensagem é enviada toda de uma vez
            connection.sendall(header + convertedMsg)
        except BrokenPipeError:
            raise CDProtoBadFormat(convertedMsg)

    @classmethod
    def recv_msg(cls, connection: socket) -> Message:
        """Receives through a connection a Message object."""

        
        header = connection.recv(2)
        msgLen = int.from_bytes(header, "big") # NOTE: convereter os bytes para int

        if not msgLen:
            # NOTE: se a mensagem não tiver tamanho, então não é uma mensagem válida
            return None
        
        msg = connection.recv(msgLen).decode('utf-8')
        
        # NOTE: tentar decodificar a mensagem
        try:
            # NOTE: tentar fazer o parse da mensagem
            encodedMsg = json.loads(msg)
        except json.JSONDecodeError:
            raise CDProtoBadFormat(msg)

        if encodedMsg["command"] == "register":
            return RegisterMessage(encodedMsg["user"])
        elif encodedMsg["command"] == "join":
            return JoinMessage(encodedMsg["channel"])
        elif encodedMsg["command"] == "message":
            return TextMessage(encodedMsg["message"], encodedMsg.get("channel", "main"), encodedMsg["ts"])
        else:
            raise CDProtoBadFormat(msg)


class CDProtoBadFormat(Exception):
    """Exception when source message is not CDProto."""

    def __init__(self, original_msg: bytes=None) :
        """Store original message that triggered exception."""
        self._original = original_msg

    @property
    def original_msg(self) -> str:
        """Retrieve original message as a string."""
        return self._original.decode("utf-8")