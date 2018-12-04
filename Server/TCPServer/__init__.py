import socket
import Queue
import threading
import sys
import cPickle
from Server.dbHandler import dbHandler

__MAXSIZE__ = 1024


class TCPServer:
    """Opens a TCP socket with host and port as arguments. Starts a thread for
       listening and each client, sending is in main thread."""

    def __init__(self, msgQueue, HOST='', PORT=0, MAXSIZE=4096):
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
        while len(self.connections) > 0:
            self.connections = [t.join(1) for t in self.connections
                                if t is not None and t.isAlive()]

    def getSocketAddress(self):
        return self.serverSckt.getsockname()


class TCPLstnr(threading.Thread):
    """Thread listening to new connections.
       Opens new thread on new connection"""

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
                print "New connection from " + str(address)
                # TODO: check if IP is in database
                connection = TCPCnxn(str(address), clientSckt,
                                     self.recvQueue)
                connection.start()
                self.connections.append(connection)
                handler = dbHandler()
                name = handler.get_user_info_from_ip(address[0])
                handler.close()
                if name is not None:
                    client = (address[0], name)
                    connection = TCPCnxn(str(address), client, clientSckt,
                                         self.recvQueue, self.msgTypes)
                    connection.start()
                    self.connections.append(connection)
                else:
                    clientSckt.shutdown(socket.SHUT_RDWR)
                    print "Connection refused"
            except socket.error:
                break

    def stop(self):
        self.killFlag.set()
        self.serverSckt.shutdown(socket.SHUT_RDWR)


class TCPCnxn(threading.Thread):
    """Thread listening to connected endpoint"""

    def __init__(self, name, client, clientSckt, recvQueue):
        super(TCPCnxn, self).__init__()
        self.name = name
        self.client = client
        self.clientSckt = clientSckt
        self.recvQueue = recvQueue
        self.killFlag = threading.Event()

    def run(self):
        print "Connection established with " + str(self.getRemoteAddress())
        while not self.killFlag.isSet():
            try:
                scktRdFile = self.clientSckt.makefile('rb')
                msg = [self, self.client]
                msg.append(cPickle.load(scktRdFile))
                self.recvQueue.put(msg)
            except EOFError:
                print str(self.getRemoteAddress()) + " socket closed"
                break
            except cPickle.UnpicklingError:
                pass
            except socket.error, error:
                print >>sys.stderr, "Socket error while receiving. Code: "\
                                    + str(error[0]) + " Message: " + error[1]
                break
        scktRdFile.close()
        self.disconnect()

    def send(self, msg):
        try:
            self.clientSckt.sendall(msg)
        except socket.error, error:
            print >>sys.stderr, "Socket error while sending. Code: "\
                                + str(error[0]) + " Message: " + error[1]
            raise

    def disconnect(self):
        self.killFlag.set()
        self.clientSckt.shutdown(socket.SHUT_WR)

    def getRemoteAddress(self):
        return self.clientSckt.getpeername()


# Example program using TCPServer
if __name__ == '__main__':
    HOST = ''
    PORT = 8888
    recvQueue = Queue.Queue()
    TCPServer = TCPServer(recvQueue, HOST, PORT)
    print "Connection open on " + str(TCPServer.getSocketAddress())

    try:
        while True:
            data = recvQueue.get()
            if data[1] is None:
                pass
            elif data[2] == 'Bye!':
                print "Disconnect request sent from "\
                      + str(data[0].getRemoteAddress())
                print "Disconnecting client"
                TCPServer.disconnect(data[0])
            else:
                print "Received data from " + str(data[0].getRemoteAddress())
                print str(data[2])
                reply = "You sent: " + data[2]
                data[0].send(reply)
    except KeyboardInterrupt:
        TCPServer.shutdown()
