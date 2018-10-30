#! /usr/bin/python

import Queue
import threading
import socket
import sys

__MAXSIZE__ = 1024


class UDPServer:
    """docstring for UDPServer."""

    def __init__(self, HOST, PORT, msgQueue, MAXSIZE=1024):
        self.HOST = HOST
        self.PORT = PORT
        self.killFlag = threading.Event()
        self.recvQueue = msgQueue
        self.sendQueue = Queue.Queue()

        global __MAXSIZE__
        __MAXSIZE__ = MAXSIZE

        try:
            self.sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sckt.settimeout(0.1)
        except socket.error, msg:
            print 'Failed to create socket. Error Code : '\
                  + str(msg[0]) + ' Message ' + msg[1]
            raise
        try:
            self.sckt.bind((HOST, PORT))
        except socket.error, msg:
            print 'Bind failed. Error Code : ' + str(msg[0])\
                  + ' Message ' + msg[1]
            raise

        threadNames = ['RCVR', 'SNDR']
        self.threads = []

        UDPRcvr = UDPReceive(threadNames[0], self.killFlag,
                             self.sckt, self.recvQueue)
        self.threads.append(UDPRcvr)
        UDPRcvr.start()
        UDPSend = UDPSender(threadNames[1], self.killFlag,
                            self.sckt, self.sendQueue)
        self.threads.append(UDPSend)
        UDPSend.start()

    def send(self, message, dest):
        toSend = []
        toSend.append(message)
        toSend.append(dest)
        self.sendQueue.put(toSend)

    def shutdown(self):
        self.killFlag.set()

        try:
            self.sendQueue.put_nowait(None)
        except Queue.Full:
            pass

        while len(self.threads) > 0:
            self.threads = [t.join(1) for t in self.threads
                            if t is not None and t.isAlive()]

        self.sckt.close()


class UDPReceive(threading.Thread):
    """Waits for UDP reception and puts items in the recvQueue
    then notifies condition 1"""

    def __init__(self, name, killFlag, sckt, recvQueue):
        super(UDPReceive, self).__init__()
        self.name = name
        self.killFlag = killFlag
        self.sckt = sckt
        self.recvQueue = recvQueue

    def run(self):
        while 1:
            try:
                newD = self.sckt.recvfrom(__MAXSIZE__)
                print self.name + ": Received message from " + str(newD[1])
                self.recvQueue.put(newD)
            except socket.timeout:
                pass
            except socket.error, msg:
                print "Socket connection error. Code: " + str(msg[0]) + \
                      "Message: " + msg[1]
                raise
            finally:
                if self.killFlag.isSet():
                    break
        print self.name + ": Thread exiting"


class UDPSender(threading.Thread):
    """Waits for item to be put in the sendQueue before sending them"""

    def __init__(self, name, killFlag, sckt, sendQueue):
        super(UDPSender, self).__init__()
        self.name = name
        self.killFlag = killFlag
        self.sckt = sckt
        self.sendQueue = sendQueue

    def run(self):
        while 1:
            try:
                toSend = self.sendQueue.get()
                if toSend is not None:
                    print self.name + ": Sending reply."
                    self.sckt.sendto(toSend[0], toSend[1])
            except socket.timeout:
                self.parent.sendQueue.put(toSend)
            except socket.error, msg:
                print "Socket connection error. Code: " + str(msg[0]) + \
                      "Message: " + msg[1]
                raise
            finally:
                if self.killFlag.isSet():
                    break
        print self.name + ": Thread exiting"


if __name__ == '__main__':
    HOST = ''    # Symbolic name meaning all available interfaces
    PORT = 8888  # Arbitrary non-privileged port
    msgQueue = Queue.Queue()

    try:
        udpserver = UDPServer(HOST, PORT, msgQueue)
    except socket.error:
        sys.exit(1)

    try:
        while 1:
            msg = msgQueue.get()
            if msg[0] == "Bye!":
                print "Received disconnection request from: " + str(msg[1])
                udpserver.send(msg[0], msg[1])
                break
            else:
                print "Received message from: " + str(msg[1])
                toSend = "You sent: " + msg[0]
                udpserver.send(toSend, msg[1])
    except KeyboardInterrupt:
        pass
    except socket.error:
        sys.exit()
    finally:
        print "Shutting down UDP Server."
        udpserver.shutdown()

    sys.exit(0)
