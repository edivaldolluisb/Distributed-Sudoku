from sudokuSocket import Server

node2 = Server('', 5001, 8001, ('', 5000))
node2.loop()
