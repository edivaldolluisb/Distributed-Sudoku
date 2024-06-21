# Distributed Sudoku Project (UPDATING)

This project develops a distributed server for solving Sudokus, using a peer-to-peer (P2P) network architecture to distribute the solving load between several nodes. Each node can receive a Sudoku to solve and communicate with other nodes to find the solution.

## Algorithm Description

The algorithm works as follows:

1. **Start**: When a node connects to the p2p network, it receives a task if there is any at the instant it joins, or when a node asks to solve a task.

2. **Sudoku Solving**: If a node receives a Sudoku to solve, it divides the problems, and sends a message to the other nodes asking them to solve. If the other nodes agree to solve the node sends them the task.
  ![Flow image]([https://github.com/edivaldolluisb/Distributed-Sudoku/blob/main/flow.pdf](https://github.com/edivaldolluisb/Distributed-Sudoku/blob/main/flow.png))
3. **Node Communication**: Nodes communicate through JSON messages containing specific commands, such as `solve`, `solution`, `keep_alive`, etc. These messages are sent via TCP/IP sockets.

4. **Solution Verification**: Once a solution is found, the node sends it back to the requester. The node that requested the solution verifies if the solution is valid and then informs the other nodes so they can update their records.

5. **Network Maintenance**: To ensure the network remains active, nodes periodically send `keep_alive` messages. If a connection fails, the node is removed from the network.

6. **Server Shutdown**: The server can be manually shut down through an interrupt signal, after which all connections are closed and resources are freed.

## How to Use

To start the server, run the `node.py` script with the appropriate command-line arguments. For example:


This will start the server on port 7000 for P2P communication and port 8000 for the HTTP server.

## Key Features

- `keep_alive`: Sends periodic messages to verify node connectivity.
- `send_solve_on_join`: Sends a Sudoku task to solve when a new node joins.
- `close_connection`: Closes a connection with another node.
- `loop`: Main server loop responsible for initializing the HTTP server and processing events.

## Contribution

Contributions are welcome. Feel free to open issues to report bugs or propose improvements.

## License

This project is licensed under the MIT license. See the `LICENSE` file for more details.


https://docs.google.com/document/d/1mloTifFc2gOXLKEOmNj2gBh1z1ZSyk1LuuMM53YsDzg/edit?usp=sharing
