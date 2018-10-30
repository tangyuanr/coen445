#! /usr/bin/python

import Queue
import threading
import socket
import sys

sendQueue = Queue.Queue()
recvQueue = Queue.Queue()

killFlag = False


class UDPReceive(threading.Thread):
    """Waits for UDP reception and puts items in the recvQueue
    then notifies condition 1"""

    def __init__(self, s, name):
        super(UDPReceive, self).__init__()
        self.sckt = s
        self.name = name

    def run(self):
        while 1:
            try:
                newD = self.sckt.recvfrom(MAX_SIZE)
                print self.name + ": Received message from " + str(newD[1])
                recvQueue.put(newD)
            except socket.timeout:
                pass
            except socket.error:
                print "Socket connection error. Code: " + str(msg[0]) + \
                      "Message: " + msg[1]
            finally:
                if killFlag:
                    break
        print self.name + ": Thread exiting"


class UDPSender(threading.Thread):
    """Waits for item to be put in the sendQueue before sending them"""

    def __init__(self, s, name):
        super(UDPSender, self).__init__()
        self.name = name
        self.sckt = s

    def run(self):
        while 1:
            try:
                toSend = sendQueue.get()  # Will block while queue is empty
                if toSend is not None:
                    print self.name + ": Sending reply."
                    self.sckt.sendto(toSend[0], toSend[1])
            except socket.timeout:
                sendQueue.put(toSend)
            except socket.error, msg:
                print "Socket connection error. Code: " + str(msg[0]) + \
                      "Message: " + msg[1]
            finally:
                if killFlag:
                    break
        print self.name + ": Thread exiting"


# class UDPServer():
HOST = ''    # Symbolic name meaning all available interfaces
PORT = 8888  # Arbitrary non-privileged port
MAX_SIZE = 1024
try:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        print 'Socket created'
    except socket.error, msg:
        print 'Failed to create socket. Error Code : ' + \
              str(msg[0]) + ' Message ' + msg[1]
        sys.exit()
    try:
        s.bind((HOST, PORT))
        print 'Socket bind complete'
    except socket.error, msg:
        print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
        sys.exit()

    threadNames = ['RCVR', 'SNDR']
    threads = []

    UDPRcvr = UDPReceive(s, threadNames[0])
    threads.append(UDPRcvr)
    UDPRcvr.start()
    UDPSend = UDPSender(s, threadNames[1])
    threads.append(UDPSend)
    UDPSend.start()

    while 1:
        newD = recvQueue.get()
        if newD[0] == "Bye!":
            print 'Bye!'
            sendQueue.put(newD)
            break
        else:
            print "Received message is: " + str(newD[0])
            sendMsg = 'You sent: ' + newD[0]
            toSend = [sendMsg, newD[1]]
            sendQueue.put(toSend)
except KeyboardInterrupt:
    pass

killFlag = True
try:
    sendQueue.put_nowait(None)
except Queue.Full:
    pass

while len(threads) > 0:
    threads = [t.join(1) for t in threads if t is not None and t.isAlive()]

s.close()
sys.exit(0)
