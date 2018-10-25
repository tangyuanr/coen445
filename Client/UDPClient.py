import socket   #for sockets
import sys  #for exit
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

except socket.error:
    print 'Failed to create socket'
    sys.exit()

host = 'localhost';
port = 8888;

while(1) :
    msg = raw_input('Enter message to send : ')

    try :
        s.sendto(msg, (host, port))
        d = s.recvfrom(1024)
        reply = d[0]
        addr = d[1]

        print 'Server reply : ' + reply

    except socket.error, msg:
        print 'Error'
