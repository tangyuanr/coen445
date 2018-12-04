#! /usr/bin/python

import socket
import threading
import sys
import cPickle


class TCPClient (threading.Thread):
    def __init__(self, msgQueue, HOST, PORT):
        super(TCPClient, self).__init__()
        self.HOST = HOST
        self.PORT = PORT
        self.recvQueue = msgQueue
        self.killFlag = threading.Event()
        self.sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sckt.connect(HOST, PORT)

    def getSocketAddress(self):
        return self.serverSckt.getsockname()

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
