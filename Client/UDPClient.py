#! /usr/bin/python

import socket   # for sockets
import sys  # for exit
import pickle

killFlag = False
RQ = 0

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

except socket.error:
    print "Failed to create socket"
    sys.exit()

host = 'localhost'
port = 8888

while not killFlag:
    messagetype = raw_input("Enter message-type: ")
    name=raw_input("Enter name: ")

    try:
        message = {
            'message-type': messagetype,
            'name': name,
            'RQ': RQ
        }
        s.sendto(pickle.dumps(message), (host, port))
        d = s.recvfrom(1024)
        reply = pickle.loads(d[0])
        addr = d[1]
        if reply == 'Bye!':
            killFlag = True
        print "Server reply: ", reply

    except socket.error, msg:
        print 'Error'

    RQ += 1

print "Closing connection"
s.close()
sys.exit(0)
