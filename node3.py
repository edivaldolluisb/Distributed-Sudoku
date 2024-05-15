from sudokuSocket import Server

node3 = Server('', 5002, 8002, ('', 5000))
node3.loop()