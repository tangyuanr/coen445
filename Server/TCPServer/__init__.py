import socket
import Queue
import threading
import sys

__MAXSIZE__ = 1024


class TCPServer:
    """docstring for TCPServer."""

    def __init__(self, HOST, PORT, msgQueue, MAXSIZE=1024):
        self.HOST = HOST
        self.PORT = PORT
        self.recvQueue = msgQueue
        self.connections = []

        global __MAXSIZE__
        __MAXSIZE__ = MAXSIZE

        try:
            self.serverSckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, msg:
            print >>sys.stderr, 'Failed to create socket. Error Code : '\
                                + str(msg[0]) + ' Message ' + msg[1]
            raise
        try:
            self.serverSckt.bind((HOST, PORT))
        except socket.error, msg:
            print >>sys.stderr, 'Bind failed. Error Code : '\
                                + str(msg[0]) + ' Message ' + msg[1]
            raise

        self.TCPLstnr = TCPLstnr('Listener', self.serverSckt,
                                 self.recvQueue, self.connections)
        self.TCPLstnr.start()

    def sendall(self, msg):
            for c in self.connections:
                c.send(msg)

    def disconnect(self, connection):
        connection.disconnect()
        connection.join()
        self.connections.remove(connection)

    def shutdown(self):
        self.TCPLstnr.stop()
        for t in self.connections:
            t.disconnect()
        while len(threads) > 0:
            threads = [t.join(1) for t in threads
                       if t is not None and t.isAlive()]


class TCPLstnr(threading.Thread):
    """Thread listening to new connections.
    Appends new connections to connections"""

    def __init__(self, name, serverSckt, recvQueue, connections):
        super(TCPLstnr, self).__init__()
        self.name = name
        self.serverSckt = serverSckt
        self.recvQueue = recvQueue
        self.connections = connections
        self.killFlag = threading.Event()

    def run(self):
        while not self.killFlag.isSet():
            try:
                self.serverSckt.listen(5)
                clientSckt, address = self.serverSckt.accept()
                connection = TCPCnxn(str(address), clientSckt,
                                     self.recvQueue)
                connection.start()
                self.connections.append(connection)
            except socket.error:
                break

    def stop(self):
        self.killFlag.set()
        self.serverSckt.shutdown(SHUT_RDWR)


class TCPCnxn(threading.Thread):
    """Thread listening to connected endpoint"""

    def __init__(self, name, clientSckt, recvQueue):
        super(TCPCnxn, self).__init__()
        self.name = name
        self.clientSckt = clientSckt
        self.recvQueue = recvQueue
        self.killFlag = threading.Event()

    def run(self):
        while not self.killFlag.isSet():
            try:
                msg = [self]
                msg.append(self.clientSckt.recv(__MAXSIZE__))
                self.recvQueue.put(msg)
            except socket.error, error:
                print >>sys.stderr, "Socket error while receiving. Code: "\
                                    + str(error[0]) + "Message: " + error[1]
                break
        self.clientSckt.close()

    def send(self, msg):
        try:
            self.clientSckt.sendall(msg)
            break
        except socket.error, error:
            print >>sys.stderr, "Socket error while sending. Code: "\
                                + str(error[0]) + "Message: " + error[1]
            raise

    def disconnect(self):
        self.killFlag.set()
        self.clientSckt.shutdown(SHUT_WR)


if __name__ == '__main__':
    
