#! /usr/bin/python

import socket   # for sockets
import sys  # for exit

killFlag = False

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

except socket.error:
    print "Failed to create socket"
    sys.exit()

host = 'localhost'
port = 8888

while not killFlag:
    msg = raw_input("Enter message to send: ")

    try:
        s.sendto(msg, (host, port))
        d = s.recvfrom(1024)
        reply = d[0]
        addr = d[1]
        if reply == 'Bye!':
            killFlag = True
        print "Server reply: " + reply

    except socket.error, msg:
        print 'Error'

print "Closing connection"
s.close()
sys.exit(0)
