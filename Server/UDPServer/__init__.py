#! /usr/bin/python

import Queue
import threading
import socket
import sys
import pickle


__MAXSIZE__ = 1024


class UDPServer:
    """docstring for UDPServer."""

    def __init__(self, HOST, PORT, msgQueue, MAXSIZE=1024):
        self.HOST = HOST
        self.PORT = PORT
        self.killFlag = threading.Event()
        self.recvQueue = msgQueue
        self.ACTION_LIST = {
            'Register': 0,
            'Deregister': 1,
            'Offer': 2
        }

        global __MAXSIZE__
        __MAXSIZE__ = MAXSIZE

        try:
            self.sckt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sckt.settimeout(0.1)
        except socket.error, msg:
            print >> sys.stderr, 'Failed to create socket. Error Code : ' \
                                 + str(msg[0]) + ' Message ' + msg[1]
            raise
        try:
            self.sckt.bind((HOST, PORT))
        except socket.error, msg:
            print >> sys.stderr, 'Bind failed. Error Code : ' + str(msg[0]) \
                                 + ' Message ' + msg[1]
            raise

        self.UDPRcvr = UDPReceive('UDPRcvr', self.killFlag,
                                  self.sckt, self.recvQueue)
        self.UDPRcvr.start()

    def send(self, message, dest):
        maxTries = 3
        while maxTries > 0:
            try:
                self.sckt.sendto(message, dest)
                break
            except socket.timeout:
                maxTries -= 1
            except socket.error, msg:
                print >> sys.stderr, "Socket connection error. Code: " \
                                     + str(msg[0]) + "Message: " + msg[1]
                raise
        if maxTries <= 0:
            raise socket.error

    def shutdown(self):
        self.killFlag.set()
        while self.UDPRcvr.is_alive():
            self.UDPRcvr.join(1)

        self.sckt.close()

    def register(self, sender_info, data_packet):
        sender_ip, sender_port = sender_info
        sender_name = data_packet['name']

    def receive(self, message):
        sender_info = message[1]
        print "sender info: " + sender_info
        data_packet = pickle.loads(message[0])
        print "data packet " + data_packet




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
                self.recvQueue.put(newD)
            except socket.timeout:
                pass
            except socket.error, msg:
                print >> sys.stderr, "Socket connection error. Code: " \
                                     + str(msg[0]) + "Message: " + msg[1]
                raise
            finally:
                self.recvQueue.put(None)
                if self.killFlag.isSet():
                    break
        print self.name + ": Thread exiting"


if __name__ == '__main__':
    HOST = ''  # Symbolic name meaning all available interfaces
    PORT = 8888  # Arbitrary non-privileged port
    msgQueue = Queue.Queue()

    try:
        udpserver = UDPServer(HOST, PORT, msgQueue)
    except socket.error:
        sys.exit(1)

    try:
        while 1:
            msg = msgQueue.get()
            if msg is None:
                continue
            if msg[0] == "Bye!":
                print "Received disconnection request from: " + str(msg[1])
                udpserver.send(msg[0], msg[1])
                break
            else:
                udpserver.receive(msg)
                print "Received message from: " + str(msg[1])
                print pickle.loads(msg[0])
                print "Sending reply."
                toSend = "You sent: " + msg[0]
                udpserver.send(toSend, msg[1])
    except KeyboardInterrupt:
        print "Ctrl-C detected!"
    except socket.error:
        raise
    finally:
        print "Shutting down UDP Server."
        udpserver.shutdown()

    sys.exit(0)
