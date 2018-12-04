#! /usr/bin/python

import socket  # for sockets
import sys  # for exit
import time
import threading
import cPickle
import Queue
from Server.UDPServer import UDPReceive
from appJar import gui

MAX_SIZE = 65535
killFlag = False
RQ = 0
SERVER_PORT = 0
SERVER_IP = ''
CLIENT_NAME = ''
CLIENT_IP = ''
CLIENT_PORT = 0
LOGGED_IN = False
TEST = 0


def test_func(btn):
    print btn
    app.setLabel('TESTING', str(TEST))


"""UI RELATED FLAGS"""
REGISTER_WINDOW_UP = False


app = gui()


# TODO: do something about the 'NEW-ITEM' message-type


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
        s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
        RQ += 1
        d = s.recvfrom(MAX_SIZE)
        reply = cPickle.loads(d[0])
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
    app.startSubWindow('Connection error handling')
    app.addMessage('Server reconnection', 'Please wait while we try to reconnect to server\n')
    app.stopSubWindow()
    app.showSubWindow('Connection error handling')
    reconnected = False
    while countdown > 0:
        try:
            message = 'CONNECT'
            s.sendto(cPickle.dumps(message), (SERVER_IP, SERVER_PORT))
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
        time.sleep(2)
        countdown -= 1

    if not reconnected:
        app.setMessage('Server reconnection', 'Connection timeout, cannot reestablish connection to server, exiting.')
        app.stop()

        s.close()
        sys.exit(0)
    else:
        app.setMessage('Server reconnection', 'Connection reestablished.')
        app.destroySubWindow('Connection error handling')
        app.showAllSubWindows()


def get_items():
    global RQ
    request = {
        'RQ': RQ,
        'message-type': 'GET-ITEMS',
        'name': CLIENT_NAME
    }
    try:
        s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
        RQ += 1
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)
        server_crash_handling()


def refresh(offer_items):
    # items = [('ID', 'Owner', 'Description', 'IP', 'Minimum', 'Finished', 'Start time', 'Winner', 'Current highest')]
    items = []
    for item in offer_items:
        items.append(list(item))
    header = [('ID', 'Owner', 'Description', 'IP', 'Bidding Port', 'Minimum', 'Finished', 'Time left', 'Winner',
               'Current highest')]
    app.setTableHeaders('Offers table', header)
    app.replaceAllTableRows('Offers table', items)


def offer_response_handler(data_packet):
    if not data_packet['success']:
        app.errorBox('Offer denied', data_packet['reason'])
    else:
        reply_message = '\n'.join(x + ': ' + str(data_packet[x]) for x in data_packet)
        app.infoBox('submissionsuccess', reply_message)
        get_items()
        app.destroySubWindow('New offer window')


def submit_offer():
    global RQ
    description = app.getEntry('Description')
    minimum = app.getEntry('Minimum')
    if description == '' or minimum < 1:
        app.errorBox('Invalid offer', 'Invalid offer')
    else:
        request = {
            'RQ': RQ,
            'name': CLIENT_NAME,
            'message-type': 'OFFER',
            'description': app.getEntry('Description'),
            'minimum': app.getEntry('Minimum')
        }
        try:
            s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
            RQ += 1
        except socket.error, msg:
            print msg
            app.errorBox('connectionerror', msg)
            server_crash_handling()


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


def offer_broadcast_handler(data_packet):
    if not LOGGED_IN:
        pass
    else:
        refresh(data_packet['offers'])


def refresh_offers_list(data_packet):
    if not LOGGED_IN:
        pass
    else:
        if not data_packet['success']:
            app.errorBox('Cannot retrieve offers list', data_packet['reason'])
        else:
            refresh(data_packet['items'])


def offers_window():
    app.startSubWindow('Offers window')
    app.addLabel('Offers window title', 'Hi ' + CLIENT_NAME)

    app.addButton('Make offer', func=make_offer)

    app.addLabel('l1', 'Active items')

    items = [('ID', 'Owner', 'Description', 'IP', 'Bidding Port', 'Minimum', 'Finished', 'Time left', 'Winner',
              'Current highest')]

    # print items
    app.addTable('Offers table', data=items, action=place_bid)
    get_items()  # retrieve offers from server

    app.addButton('Refresh', func=get_items)

    app.stopSubWindow()
    app.showSubWindow('Offers window')


def register_handler(data_packet):
    if not data_packet['success']:
        app.errorBox('Registration failed', data_packet['reason'])
    else:
        global CLIENT_NAME
        CLIENT_NAME = data_packet['name']
        app.destroySubWindow('Register login window')

        offers_window()


def register():
    global RQ
    name = app.getEntry('Name')
    ip = app.getEntry('Bidding IP')
    if name == '' or ip == '':
        app.errorBox('Empty username', 'Username cannot be empty')
    else:
        request = {
            'RQ': RQ,
            'name': name,
            'ip': ip,
            'message-type': 'REGISTER'
        }
        try:
            s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
            RQ += 1
        except socket.error, msg:
            print msg
            app.errorBox('connectionerror', msg)
            server_crash_handling()


def login_failed_handler(data_packet):
    app.errorBox('Login failed', data_packet['reason'])


def login_success_handler(data_packet):
    global CLIENT_NAME
    CLIENT_NAME = data_packet['name']
    app.destroySubWindow('Register login window')

    offers_window()


def login():
    global RQ
    name = app.getEntry('Name')
    ip = app.getEntry('Bidding IP')
    if name == '' or ip == '':
        app.errorBox('Empty user name', 'Fields cannot be empty')
    else:
        request = {
            'RQ': RQ,
            'name': name,
            'ip': ip,
            'message-type': 'LOGIN'
        }
        try:
            s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
            RQ += 1
        except socket.error, msg:
            print msg
            app.errorBox('connectionerror', msg)
            server_crash_handling()


def register_window():
    app.hideSubWindow('Initiation window')  # cleanse window

    # app.startSubWindow('Register login window')
    # app.addLabel('instruction', text='Please log in or register with your unique name id and server port')
    # app.addLabelEntry('Bidding IP')
    # app.addLabelEntry('Name')
    # app.addButton('Register', row=3, column=0, func=register)
    # app.addButton('Login', row=3, column=1, func=login)
    # app.stopSubWindow()

    # app.show()
    app.showSubWindow('Register login window')
    print 'here'


ACTION_LIST = {
    'OFFER-BROADCAST': 0,
    'UNREGISTER': register_handler,
    'REGISTERED': register_handler,
    'LOGIN-FAILED': login_failed_handler,
    'LOGIN-CONF': login_success_handler,
    'DEREG-DENIED': 0,
    'DEREG-CONF': 0,
    'NEW-ITEM': 0,
    'ITEM-LIST': refresh_offers_list,
    'OFFER-DENIED': offer_response_handler,
    'OFFER-CONF': offer_response_handler,
    'LOGOUT-DENIED': 0,
    'LOGOUT-CONF': 0
}


def action_dispatcher(data_packet):
    action = data_packet['message-type']
    ACTION_LIST[action](data_packet)

# UDP listener
def msgHandler():
    global msgQueue, REGISTER_WINDOW_UP
    print 'HERE AT MSGHANDLER'
    try:
        while 1:
            message = msgQueue.get()
            if message is None:
                continue
            else:
                data_packet = cPickle.loads(message[0])
                app.queueFunction(action_dispatcher, data_packet)
    except KeyboardInterrupt:
        print "Keyboard interrupt"
    except socket.error as e:
        print e.message
        raise
    finally:
        print "client shut down"
        s.close()
    sys.exit()


def connect():
    port = int(app.getEntry('Server port'))
    ip = app.getEntry('Server ip')
    print ip, port
    try:
        host = ip
        message = 'CONNECT'
        s.sendto(cPickle.dumps(message), (host, port))
        # print 'line24'
        # d = s.recvfrom(MAX_SIZE)
        # reply = d[0]
        # addr = d[1]
        reply = msgQueue.get()[0]
        print reply
        if reply == 'OK':
            global SERVER_PORT, SERVER_IP
            SERVER_PORT = port
            SERVER_IP = ip

            # UDP listener starts here
            app.thread(msgHandler)

            register_window()

        else:
            app.errorBox('error', 'Connection to server cannot be established')
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)
        server_crash_handling()


def initiate(ip, port):
    initiation_complete = 'Initiation complete, your address: ' + ip + ', ' + str(port[1])
    print initiation_complete

    # app.startSubWindow('Initiation window', stopfunc=checkStop)
    app.startSubWindow('Initiation window')

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

    app.startSubWindow('Register login window')
    app.addLabel('instruction', text='Please log in or register with your unique name id and server port')
    app.addLabelEntry('Bidding IP')
    app.addLabelEntry('Name')
    app.addButton('Register', row=3, column=0, func=register)
    app.addButton('Login', row=3, column=1, func=login)
    app.stopSubWindow()
    # app.showSubWindow('Register login window')

    app.go(startWindow='Initiation window')


# class UDPReceive(threading.Thread):
#     """Copied UDPServer's UDPReceive function"""
#
#     def __init__(self, sckt, rcvQ):
#         super(UDPReceive, self).__init__()
#         self.socket = sckt
#         self.receiveQueue = rcvQ
#
#     def run(self):
#         while 1:
#             try:
#                 data = self.socket.recvfrom(MAX_SIZE)
#                 self.receiveQueue.put(data)
#             except socket.timeout:
#                 pass
#             except socket.error, msg:
#                 print msg
#             finally:
#                 break


if __name__ == '__main__':
    client_ip = ''
    client_port = 0
    msgQueue = Queue.Queue()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', 0))
        client_ip = socket.gethostbyname(socket.gethostname())
        client_port = socket.socket.getsockname(s)
        UDPListener = UDPReceive('Client UDP', threading.Event(), s, msgQueue)
        UDPListener.start()

        initiate(client_ip, client_port)
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
#         s.sendto(cPickle.dumps(message), (host, port))
#         d = s.recvfrom(MAX_SIZE)
#         reply = cPickle.loads(d[0])
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
