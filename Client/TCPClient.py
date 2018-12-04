#! /usr/bin/python

import socket
import Queue
import threading
import sys
import cPickle


class TCPClient (threading.Thread):
    def __init__(self, msgQueue, HOST, PORT):
        super(TCPClient, self).__init__()
        self.HOST = HOST
        self.PORT = PORT
        address = (HOST, PORT)
        self.recvQueue = msgQueue
        self.killFlag = threading.Event()
        self.sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sckt.connect(address)

    def getSocketAddress(self):
        return self.sckt.getsockname()

    def run(self):
        print "Connection established with " + str(self.getRemoteAddress())
        while not self.killFlag.isSet():
            try:
                scktRdFile = self.clientSckt.makefile('rb')
                self.recvQueue.put(cPickle.load(scktRdFile))
            except EOFError:
                print str(self.sckt.getRemoteAddress()) + " socket closed"
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
        self.sckt.shutdown(socket.SHUT_WR)

    def getRemoteAddress(self):
        return self.sckt.getpeername()


if __name__ == '__main__':
    Host = ''
    Port = 8888
    msgQueue = Queue.Queue()
    client = TCPClient(msgQueue, Host, Port)
    rq = 0
    amt = 10
    try:
        while(1):
            nbid = {
                "RQ": rq,
                "ID": 99,
                "AMT": amt
            }
            rq += 1
            amt += 10
            client.send(cPickle.dumps(nbid, -1))
            msg = msgQueue.get(True, 1)
            if msg is not None:
                if msg["T"] is "HI":
                    print "Highest bid is " + str(msg["AMT"])
    except sys.error:
        pass
