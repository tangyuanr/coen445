#! /usr/bin/python

import socket
import sys

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
killFlag = False

# Connect the socket to the port where the server is listening
server_address = ('localhost', 8888)
print >>sys.stderr, 'connecting to %s port %s' % server_address
sock.connect(server_address)
while not killFlag:
    msg = raw_input("Enter message to send: ")

    try:
        sock.sendall(msg)
        data, reply = sock.recv(1024)
        if reply == 'Bye!':
            killFlag = True
        print str(reply)

    except socket.error, msg:
        print 'Error'

sock.shutdown(socket.SHUT_WR)
sock.close()
