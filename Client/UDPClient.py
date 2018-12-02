#! /usr/bin/python

import socket  # for sockets
import sys  # for exit
import pickle
from appJar import gui

app = gui()
killFlag = False
RQ = 0
SERVER_PORT = 0
CLIENT_NAME = ''


def get_items():
    global RQ
    request = {
        'RQ': RQ,
        'message-type': 'GET-ITEMS',
        'name': CLIENT_NAME
    }
    try:
        s.sendto(pickle.dumps(request), ('localhost', SERVER_PORT))
        RQ += 1
        d = s.recvfrom(1024)
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


def place_bid():  # TODO: patch client to TCP bidding, also make sure the UDPServer sets each new offer with valid TCP port
    print app.getTabbedFrameSelectedTab('TabbedFrame')


def bidding_window():
    app.startSubWindow('Bidding window')
    app.addLabel('Bidding window title', 'Hi ' + CLIENT_NAME)
    app.addLabel('l1', 'Active items')

    app.startTabbedFrame('TabbedFrame')

    items = get_items()
    for item in items:
        item_id = str(item[0])
        app.startTab(item_id)
        app.addTextArea(item_id)
        # content = '\n'.join([str(x) for x in item])
        content = 'Owner: ' + item[1] + '\nDescription: ' + item[2] + '\nMinimum: ' + str(
            item[4]) + '\nCurrent Highest Bid: ' + str(item[8]) + '\nBid Start Time: ' + item[6]
        app.setTextArea(item_id, content)
        app.stopTab()
    app.stopTabbedFrame()

    app.addButton('Bid on this!', func=place_bid)

    app.stopSubWindow()
    app.showSubWindow('Bidding window')


def register():
    global RQ
    name = app.getEntry('Name')
    request = {
        'RQ': RQ,
        'name': name,
        'message-type': 'REGISTER'
    }
    try:
        s.sendto(pickle.dumps(request), ('localhost', SERVER_PORT))
        RQ += 1
        d = s.recvfrom(1024)
        reply = pickle.loads(d[0])
        print reply
        if not reply['success']:
            app.errorBox('connectionerror', reply['reason'])
        else:
            global CLIENT_NAME
            CLIENT_NAME = name
            app.hideSubWindow('Register login window')

            bidding_window()
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)


def login():
    global RQ
    name = app.getEntry('Name')
    request = {
        'RQ': RQ,
        'name': name,
        'message-type': 'LOGIN'
    }
    try:
        s.sendto(pickle.dumps(request), ('localhost', SERVER_PORT))
        RQ += 1
        d = s.recvfrom(1024)
        reply = pickle.loads(d[0])
        print reply
        if not reply['success']:
            app.errorBox('connectionerror', reply['reason'])
        else:
            global CLIENT_NAME
            CLIENT_NAME = name
            RQ += 1
            app.hideSubWindow('Register login window')

            bidding_window()
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)


def register_window():
    app.hideSubWindow('Initiation window')  # cleanse window

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
    print port
    try:
        host = 'localhost'
        message = 'CONNECT'
        s.sendto(pickle.dumps(message), (host, port))
        # print 'line24'
        d = s.recvfrom(1024)
        reply = d[0]
        addr = d[1]
        print reply
        if reply == 'OK':
            global SERVER_PORT
            SERVER_PORT = port
            register_window()
        else:
            app.addLabel('error', 'Connection to server cannot be established')
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)


def initiate():
    initiation_complete = 'Initiation complete, your address: ' + s.getsockname()[0] + ', ' + str(s.getsockname()[1])
    print initiation_complete

    app.startSubWindow('Initiation window')

    app.addLabel('initiate', text=initiation_complete)
    """Try to connect to UDP server"""
    app.addLabel('serverconnection', text='Please enter the server port number to establish connection')
    app.addNumericEntry('Server port')
    app.setEntryMaxLength('Server port', 5)
    app.addButton('server_connect', connect)
    app.stopSubWindow()

    app.go(startWindow='Initiation window')


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

host = 'localhost'
port = int(raw_input('Enter server port: '))

while not killFlag:
    messagetype = raw_input("Enter message-type: ")
    name = raw_input("Enter name: ")

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
