"""Protocol for node - Computação Distribuida Final Project"""
import json
from datetime import datetime
from socket import socket


class Message:
    """Message Type."""

    def __init__(self, command):
        """Initialize message with command"""
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
    """Message to join the network."""
    def __init__(self, bindPoint, reply, ip):
        super().__init__("join")
        self.channel = bindPoint
        self.reply = reply
        self.ip = ip

        # fzr a convertion para json
        msg = {
            "command": self.command,
            "bindPoint": self.channel,
            "reply": self.channel,
            "ip": self.channel,
        }
        self.toJson(msg)


    def __str__(self):
        return self._msg
    


class JoinReply(Message):
    """Message with all needed info to join the network."""
    def __init__(self, bindPoint, ip, data):
        super().__init__("join_reply")
        self.bindPoint = bindPoint
        self.ip = ip
        self.data = data
    
        msg = {
            "command": self.command,
            "bindPoint": self.bindPoint,
            "data": self.data,
            "ip": self.ip
        }
        self.toJson(msg)

    
    def __str__(self):
        return self._msg
    

class AskToSolve(Message):
    """Message to ask for avability to solve a sudoku."""
    def __init__(self):
        super().__init__("agToSolve")
    
        msg = {
            "command": self.command
        }
        self.toJson(msg)

    
    def __str__(self):
        return self._msg
        
    
class Solve(Message):
    """Message to solve a subproblem."""

    def __init__(self, task, taskid):
        super().__init__("solve")
        self.sudoku = task
        self.taskid = taskid

        msg = {
            "command": self.command,
            "sudoku": self.sudoku,
            "sudokuId": self.taskid
            }

        self.toJson(msg)

class Network(Message):
    """Message to ask for the network connections."""

    def __init__(self):
        super().__init__("network")

        msg = {"command": self.command}

        self.toJson(msg)

class NetworkUpdate(Message):
    """Message to update the network."""

    def __init__(self, network, validations):
        super().__init__("update_network")
        self.network = network
        self.validations = validations

        msg = {"command": self.command,
               "network": self.network,
               "validations": self.validations
               }

        self.toJson(msg)

class Solution(Message):
    """Message to send a solution to a sudoku."""

    def __init__(self, sudoku, sudokuId, solution):
        super().__init__("solution")
        self.sudoku = sudoku
        self.sudokuId = sudokuId
        self.solution = solution

        msg = {
            "command": self.command,
            "sudoku": self.sudoku,
            "sudokuId": self.sudokuId,
            "solution": self.solution
            }

        self.toJson(msg)

class Stop(Message):
    """Message to stop solving a sudoku."""

    def __init__(self, sudokuId):
        super().__init__("stop")
        self.sudokuId = sudokuId

        msg = {
            "command": self.command,
            "sudokuId": self.sudokuId
            }

        self.toJson(msg)

class KeepAlive(Message):
    """Message to ask for node ping."""

    def __init__(self, solved, validations, IP):
        super().__init__("keep_alive")
        self.solved = solved
        self.validations = validations
        self.IP = IP

        msg = {
            "command": self.command,
            "status": {
                "solved": self.solved,
                "validations": self.validations,
            },
                "IP": self.IP
            }

        self.toJson(msg)

class KeepAliveReply(Message):
    """Message to confirm node ping."""

    def __init__(self, task, taskid):
        super().__init__("keep_alive_reply")
        self.sudoku = task
        self.taskid = taskid

        msg = {"command": self.command}

        self.toJson(msg)   

class CDProto:
    """Computação Distribuida Protocol."""

    @classmethod
    def join(cls, bindPoint, reply, ip):
        """Join the network."""
        return JoinMessage(bindPoint, reply, ip)
    
    @classmethod
    def join_reply(cls, bindPoint, ip, data):
        """Reply to a join message."""
        return JoinReply(bindPoint, ip, data)
    
    @classmethod
    def ask_to_solve(cls):
        """Ask for avability to solve a sudoku."""
        return AskToSolve()
    
    @classmethod
    def solve(cls, task, taskid):
        """Solve a sudoku."""
        return Solve(task, taskid)
    
    @classmethod
    def network(cls):
        """Ask for the network connections."""
        return Network()
    
    @classmethod
    def network_update(cls, network, validations):
        """Update the network."""
        return NetworkUpdate(network, validations)
    
    @classmethod
    def solution(cls, sudoku, sudokuId, solution):
        """Send a solution to a sudoku."""
        return Solution(sudoku, sudokuId, solution)
    
    @classmethod
    def stop(cls, sudokuId):
        """Stop solving a sudoku."""
        return Stop(sudokuId)
    
    @classmethod
    def keep_alive(cls, solved, validations, IP):
        """Ask for node ping."""
        return KeepAlive(solved, validations, IP)
    
    @classmethod
    def keep_alive_reply(cls, task, taskid):
        """Confirm node ping."""
        return KeepAliveReply(task, taskid)

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

        if encodedMsg["command"] == "join":
            return JoinMessage(encodedMsg["bindPoint"], encodedMsg["reply"], encodedMsg["ip"])
        elif encodedMsg["command"] == "join_reply":
            return JoinReply(encodedMsg["bindPoint"], encodedMsg["ip"], encodedMsg["data"])
        elif encodedMsg["command"] == "ask_to_solve":
            return AskToSolve()
        elif encodedMsg["command"] == "solve":
            return Solve(encodedMsg["sudoku"], encodedMsg["sudokuId"])
        elif encodedMsg["command"] == "network":
            return Network()
        elif encodedMsg["command"] == "update_network":
            return NetworkUpdate(encodedMsg["network"], encodedMsg["validations"])
        elif encodedMsg["command"] == "solution":
            return Solution(encodedMsg["sudoku"], encodedMsg["sudokuId"], encodedMsg["solution"])
        elif encodedMsg["command"] == "stop":
            return Stop(encodedMsg["sudokuId"])
        elif encodedMsg["command"] == "keep_alive":
            return KeepAlive(encodedMsg["status"]["solved"], encodedMsg["status"]["validations"], encodedMsg["IP"])
        elif encodedMsg["command"] == "keep_alive_reply":
            return KeepAliveReply(encodedMsg["sudoku"], encodedMsg["sudokuId"])
        
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