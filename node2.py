from sudokuSocket import Server

# node2 = Server('', 5001, 8001, ('', 5000))
# node2.loop()

node4 = Server('', 5003, 8003, ('', 5001))
node4.loop()
