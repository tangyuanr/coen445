#! /usr/bin/python

import socket  # for sockets
import sys  # for exit
import time
import pickle
from appJar import gui

MAX_SIZE = 65535
killFlag = False
RQ = 0
SERVER_PORT = 0
SERVER_IP = ''
CLIENT_NAME = ''
LOGGED_IN = False

app = gui()


def checkStop():
    print "UESR IS CLOSING WINDOW"
    if LOGGED_IN:
        status = deregister()
        if status is not True:
            return False
        s.close()
        print "socket closed"
        sys.exit()
        # return status
    else:
        s.close()
        print "socket closed"
        sys.exit()
        # return True


app.topLevel.protocol('WM_DELETE_WINDOW', checkStop)
app.setStopFunction(checkStop)


def deregister():
    global RQ
    request = {
        'RQ': RQ,
        'name': CLIENT_NAME,
        'message-type': 'DEREGISTER'
    }
    try:
        s.sendto(pickle.dumps(request), (SERVER_IP, SERVER_PORT))
        RQ += 1
        d = s.recvfrom(MAX_SIZE)
        reply = pickle.loads(d[0])
        print reply
        if not reply['success']:
            app.errorBox('connectionerror', reply['reason'])
            return False, reply['reason']
        else:
            return True
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)
        server_crash_handling()


def server_crash_handling():
    app.hideAllSubWindows()
    # TODO: destroy all bidding windows + error handling in TCP instances
    countdown = 30
    app.addMessage('Server reconnection', 'Please wait while we try to reconnect to server\n')
    reconnected = False
    while countdown > 0:
        try:
            message = 'CONNECT'
            s.sendto(pickle.dumps(message), (SERVER_IP, SERVER_PORT))
            # print 'line24'
            d = s.recvfrom(MAX_SIZE)
            reply = d[0]
            addr = d[1]
            print reply
            if reply == 'OK':
                reconnected = True
                break
                # connection reestablished
        except socket.error, msg:
            print msg
        app.setMessage('Server reconnection',
                       'Please wait while we try to reconnect to server\n' + str(countdown) + ' seconds left')
        time.sleep(1)
        countdown -= 1

    if not reconnected:
        app.setMessage('Server reconnection', 'Connection timeout, cannot reestablish connection to server, exiting.')
        app.stop()

        s.close()
        sys.exit(0)
    else:
        app.setMessage('Server reconnection', 'Connection reestablished.')
        app.showAllSubWindows()


def get_items():
    global RQ
    request = {
        'RQ': RQ,
        'message-type': 'GET-ITEMS',
        'name': CLIENT_NAME
    }
    try:
        s.sendto(pickle.dumps(request), (SERVER_IP, SERVER_PORT))
        RQ += 1
        d = s.recvfrom(MAX_SIZE)
        reply = pickle.loads(d[0])
        print reply
        if not reply['success']:
            app.errorBox('connectionerror', reply['reason'])
        else:
            RQ += 1
            return reply['items']
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)
        server_crash_handling()


def refresh():
    # items = [('ID', 'Owner', 'Description', 'IP', 'Minimum', 'Finished', 'Start time', 'Winner', 'Current highest')]
    items = []
    for item in get_items():
        items.append(list(item))
    app.replaceAllTableRows('Offers table', items)


def submit_offer():
    global RQ
    request = {
        'RQ': RQ,
        'name': CLIENT_NAME,
        'message-type': 'OFFER',
        'description': app.getEntry('Description'),
        'minimum': app.getEntry('Minimum')
    }
    temp_RQ = RQ
    try:
        s.sendto(pickle.dumps(request), (SERVER_IP, SERVER_PORT))

        while 1:

            d = s.recvfrom(MAX_SIZE)
            reply = pickle.loads(d[0])
            print reply
            if reply['RQ'] != temp_RQ:
                continue
            else:
                break
        if not reply['success']:
            app.errorBox('connectionerror', reply['reason'])
        else:
            reply_message = '\n'.join(x + ': ' + str(reply[x]) for x in reply)
            app.infoBox('submissionsuccess', reply_message)
            refresh()
            app.destroySubWindow('New offer window')
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)
        server_crash_handling()
    RQ += 1


def make_offer():
    pass
    app.startSubWindow('New offer window')
    app.addLabel('l2', 'Description: ', row=0, column=0)
    app.addEntry('Description', row=0, column=1)
    app.addLabel('l3', 'Minimum amount: ', row=1, column=0)
    app.addNumericEntry('Minimum', row=1, column=1)
    app.addButton('Submit offer', func=submit_offer, row=2)
    app.stopSubWindow()

    app.showSubWindow('New offer window')


def place_bid(
        rowNumber):  # TODO: patch client to TCP bidding, also make sure the UDPServer sets each new offer with valid TCP port
    offer_info = app.getTableRow('Offers table', rowNumber)
    print offer_info
    offer_id = offer_info[0]
    app.startSubWindow('Bidding window ' + str(offer_id))
    app.addLabel('l5', 'Biddings for item ' + str(offer_id))

    # TODO: request bidding data from TCP Server and start a table

    app.stopSubWindow()
    app.showSubWindow('Bidding window ' + str(offer_id))


def offers_window():
    app.startSubWindow('Offers window')
    app.addLabel('Offers window title', 'Hi ' + CLIENT_NAME)

    app.addButton('Make offer', func=make_offer)

    app.addLabel('l1', 'Active items')

    items = [('ID', 'Owner', 'Description', 'IP', 'Bidding Port', 'Minimum', 'Finished', 'Time left', 'Winner',
              'Current highest')]
    for item in get_items():
        items.append(list(item))
    # print items
    app.addTable('Offers table', data=items, action=place_bid)
    app.addButton('Refresh', func=refresh)

    app.stopSubWindow()
    app.showSubWindow('Offers window')


def register():
    global RQ
    name = app.getEntry('Name')
    request = {
        'RQ': RQ,
        'name': name,
        'message-type': 'REGISTER'
    }
    try:
        s.sendto(pickle.dumps(request), (SERVER_IP, SERVER_PORT))
        RQ += 1
        d = s.recvfrom(MAX_SIZE)
        reply = pickle.loads(d[0])
        print reply
        if not reply['success']:
            app.errorBox('connectionerror', reply['reason'])
        else:
            global CLIENT_NAME
            CLIENT_NAME = name
            app.destroySubWindow('Register login window')

            offers_window()
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)
        server_crash_handling()


def login():
    global RQ
    name = app.getEntry('Name')
    request = {
        'RQ': RQ,
        'name': name,
        'message-type': 'LOGIN'
    }
    try:
        s.sendto(pickle.dumps(request), (SERVER_IP, SERVER_PORT))
        RQ += 1
        d = s.recvfrom(MAX_SIZE)
        reply = pickle.loads(d[0])
        print reply
        if not reply['success']:
            app.errorBox('connectionerror', reply['reason'])
        else:
            global CLIENT_NAME
            CLIENT_NAME = name
            RQ += 1
            app.destroySubWindow('Register login window')

            offers_window()
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)
        server_crash_handling()


def register_window():
    app.destroySubWindow('Initiation window')  # cleanse window

    app.startSubWindow('Register login window')
    app.addLabel('instruction', text='Please log in or register with your unique name id and server port')
    app.addLabelEntry('Name')
    app.addButton('Register', row=2, column=0, func=register)
    app.addButton('Login', row=2, column=1, func=login)
    app.stopSubWindow()

    # app.show()
    app.showSubWindow('Register login window')


def connect():
    port = int(app.getEntry('Server port'))
    ip = app.getEntry('Server ip')
    print ip, port
    try:
        host = ip
        message = 'CONNECT'
        s.sendto(pickle.dumps(message), (host, port))
        # print 'line24'
        d = s.recvfrom(MAX_SIZE)
        reply = d[0]
        addr = d[1]
        print reply
        if reply == 'OK':
            global SERVER_PORT, SERVER_IP
            SERVER_PORT = port
            SERVER_IP = ip
            register_window()
        else:
            app.addLabel('error', 'Connection to server cannot be established')
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)
        server_crash_handling()


def initiate():
    initiation_complete = 'Initiation complete, your address: ' + s.getsockname()[0] + ', ' + str(s.getsockname()[1])
    print initiation_complete

    app.startSubWindow('Initiation window', stopfunc=checkStop)

    app.addLabel('initiate', text=initiation_complete)
    """Try to connect to UDP server"""
    app.addLabel('serverconnection', text='Please enter the server port number to establish connection')
    app.addLabel('l34', 'Enter server IP:')
    app.addEntry('Server ip')
    app.addLabel('l2342', 'Enter server port:')
    app.addNumericEntry('Server port')
    app.setEntryMaxLength('Server port', 5)
    app.addButton('server_connect', connect)
    app.stopSubWindow()

    app.go(startWindow='Initiation window')


# class broadcastReceiver(threading.Thread):
#     def __init__(self, sckt, rcvq):
#         super(broadcastReceiver, self).__init__()
#         self.socket = sckt
#         self.receiveQueue = rcvq
#
#     def run(self):
#         while 1:
#             try:
#


if __name__ == '__main__':
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', 0))
        initiate()
    except socket.error:
        print "Failed to create socket"
        app.errorBox('initiate', 'Failed to create socket')
        app.go()
        sys.exit()

#
# host = 'localhost'
# port = int(raw_input('Enter server port: '))
#
# while not killFlag:
#     messagetype = raw_input("Enter message-type: ")
#     name = raw_input("Enter name: ")
#
#     try:
#         message = {
#             'message-type': messagetype,
#             'name': name,
#             'RQ': RQ
#         }
#         s.sendto(pickle.dumps(message), (host, port))
#         d = s.recvfrom(MAX_SIZE)
#         reply = pickle.loads(d[0])
#         addr = d[1]
#         if reply == 'Bye!':
#             killFlag = True
#         print "Server reply: ", reply
#
#     except socket.error, msg:
#         print 'Error'
#
#     RQ += 1
#
# print "Closing connection"
# s.close()
# sys.exit(0)
