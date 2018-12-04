#! /usr/bin/python

import socket  # for sockets
import sys  # for exit
import time
import threading
import cPickle
import Queue
from Server.UDPServer import UDPReceive
from appJar import gui
from TCPClient import TCPClient
from Bidding import Bidding

MAX_SIZE = 65535
REACTION_LIST = {
    'REGISTER': ['UNREGISTER', 'REGISTERED'],
    'DEREGISTER': ['DEREG-DENIED', 'DEREG-CONF'],
    'OFFER': ['OFFER-DENIED', 'OFFER-CONF'],
    'LOGIN': ['LOGIN-FAILED', 'LOGIN-CONF'],
    'GET-ITEMS': ['ITEM-LIST'],
    'LOGOUT': ['LOGOUT-DENIED', 'LOGOUT-CONF']
}

WAIT_REPLY = []
CURRENT_ACTION = ''
killFlag = False
RQ = 0
SERVER_PORT = 0
SERVER_IP = ''
CLIENT_NAME = ''
CLIENT_IP = ''
CLIENT_PORT = 0
LOGGED_IN = False
TEST = 0
CURRENT_BIDS = []


def test_func(btn):
    print btn
    app.setLabel('TESTING', str(TEST))


"""UI RELATED FLAGS"""
REGISTER_WINDOW_UP = False

app = gui('Main')


def checkStop():
    print "UESR IS CLOSING WINDOW"
    if LOGGED_IN:
        deregister()
    else:
        s.close()
        print "socket closed"
        sys.exit(1)
        # return True


app.topLevel.protocol('WM_DELETE_WINDOW', checkStop)
app.setStopFunction(checkStop)


def bid_over_handler(data_packet):
    if data_packet['message-type'] == 'NOT SOLD':
        app.infoBox('Item ' + data_packet['item-id'] + ' not sold', data_packet['reason'])
    else:
        app.infoBox('Item ' + data_packet['item-id'] + ' sold',
                    'Your item has been sold!\nWinner: ' + data_packet['name'] +
                    '\nWinner IP: ' + data_packet['winnerIP'] +
                    '\nWinner port: ' + str(data_packet['winnerPort']) +
                    '\nFinal price: ' + str(data_packet['amount']))


def dereg_handler(data_packet):
    global LOGGED_IN
    if data_packet['success'] is not True:
        app.errorBox('Deregistration failed', data_packet['reason'])
    else:
        LOGGED_IN = False
        app.stop()
        s.close()
        sys.exit(1)


def deregister():
    global RQ, CURRENT_ACTION
    request = {
        'RQ': RQ,
        'name': CLIENT_NAME,
        'message-type': 'DEREGISTER'
    }
    WAIT_REPLY.append((RQ, 'DEREGISTER'))
    s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
    print '\nRequest:', request
    CURRENT_ACTION = 'DEREGISTER'
    RQ += 1


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
            print countdown
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

        time.sleep(2)
        countdown -= 1

    if not reconnected:
        app.setMessage('', 'Connection timeout, cannot reestablish connection to server, exiting.')
        app.stop()

        s.close()
        sys.exit(1)
    else:
        app.setMessage('Server reconnection', 'Connection reestablished.')
        app.destroySubWindow('Connection error handling')
        app.showAllSubWindows()


def get_items():
    global RQ, CURRENT_ACTION
    request = {
        'RQ': RQ,
        'message-type': 'GET-ITEMS',
        'name': CLIENT_NAME
    }
    try:
        WAIT_REPLY.append((RQ, 'GET-ITEMS'))
        s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
        print 'Request: ', request
        CURRENT_ACTION = 'GET-ITEMS'
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
    # app.setTableHeaders('Offers table ' + CLIENT_NAME, header)
    app.replaceAllTableRows('Offers table ' + CLIENT_NAME, items)


def offer_response_handler(data_packet):
    if not data_packet['success']:
        app.errorBox('Offer denied', data_packet['reason'])
    else:
        reply_message = '\n'.join(x + ': ' + str(data_packet[x]) for x in data_packet)
        app.infoBox('submissionsuccess', reply_message)
        get_items()
        app.destroySubWindow('New offer window')


def submit_offer():
    global RQ, CURRENT_ACTION
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
            WAIT_REPLY.append((RQ, 'OFFER'))
            s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
            print 'Request: ', request
            CURRENT_ACTION = 'OFFER'
            RQ += 1
        except socket.error, msg:
            print msg
            app.errorBox('connectionerror', msg)
            server_crash_handling()


def make_offer():
    pass
    app.startSubWindow('New offer window', stopfunc=bidding_stop_func)
    app.addLabel('l2', 'Description: ', row=0, column=0)
    app.addEntry('Description', row=0, column=1)
    app.addLabel('l3', 'Minimum amount: ', row=1, column=0)
    app.addNumericEntry('Minimum', row=1, column=1)
    app.addButton('Submit offer', func=submit_offer, row=2)
    app.stopSubWindow()

    app.showSubWindow('New offer window')


def bidding_stop_func(win):
    print win
    global CURRENT_BIDS
    print CURRENT_BIDS
    app.destroySubWindow(win)
    CURRENT_BIDS.remove(int(win) - 1)


def bidding_thread_handler(ID, Owner, Description, IP, BidPort, Minimum, Finished, Timeleft, Winner, Highest):
    window_name = str(ID)
    print window_name
    print ID, Owner, Description, IP, BidPort, Minimum, Finished, Timeleft, Winner, Highest
    # bidding_queue = Queue.Queue()
    # bidding_tcp_client = TCPClient(bidding_queue, '', 0)
    # bidding_tcp_client.start()

    count = 0
    while 1:
        print 'thread of' + window_name
        # app.setLabel('label' + ID, str(count))
        # app.getLabel('label' + ID)
        #
        # count += 1
        # time.sleep(1)


def place_bid(
        rowNumber):  # TODO: patch client to TCP bidding, also make sure the UDPServer sets each new offer with valid TCP port
    global CURRENT_BIDS
    if rowNumber in CURRENT_BIDS:
        app.errorBox('Duplicate bidding window', 'Cannot open multiple bid windows on the same item')

    else:

        CURRENT_BIDS.append(rowNumber)
        offer_info = app.getTableRow('Offers table ' + CLIENT_NAME, rowNumber)
        print offer_info

        # new_bidding = Bidding(offer_info, CLIENT_NAME, CLIENT_IP)
        # new_bidding.start()

        offer_id = offer_info[0]
        offer_map = {
            'ID': offer_info[0], 'Owner': offer_info[1], 'Description': offer_info[2], 'IP': offer_info[3],
            'BidPort': offer_info[4], 'Minimum': offer_info[5], 'Finished': offer_info[6],
            'Timeleft': offer_info[7], 'Winner': offer_info[8], 'Highest': offer_info[9]
        }

        window_name = str(offer_id)
        app.startSubWindow(window_name, stopfunc=bidding_stop_func, threadfunc=bidding_thread_handler,
                           threadArgs=offer_map)
        app.addLabel('label' + str(offer_id), 'Biddings for item ' + str(offer_id))
        print "label " + str(offer_id)

        app.addNumericEntry('Bid'+str(offer_id))
        app.addButton('submit'+str(offer_id), func=None)  # TODO: add submit bid function here

        app.stopSubWindow()
        app.showSubWindow(str(offer_id))


def new_item_handler(data_packet):
    app.infoBox(title='New arrival: ' + str(data_packet['item-id']),
                message='The auction for a new item has just begun, please refresh the offers page to view more details')


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
    app.startSubWindow('Offers window ' + CLIENT_NAME, stopfunc=checkStop)
    app.addLabel('Offers window title', 'Hi ' + CLIENT_NAME)

    app.addButton('Make offer', func=make_offer)

    app.addLabel('l1', 'Active items')

    items = ('ID', 'Owner', 'Description', 'IP', 'Bidding Port', 'Minimum', 'Finished', 'Time left', 'Winner',
             'Current highest')

    # print items
    app.addTable('Offers table ' + CLIENT_NAME, data=items, action=place_bid)
    app.setTableHeaders('Offers table ' + CLIENT_NAME, data=items)
    get_items()  # retrieve offers from server

    app.addButton('Refresh', func=get_items)

    app.stopSubWindow()
    app.showSubWindow('Offers window ' + CLIENT_NAME)


def register_handler(data_packet):
    if not data_packet['success']:
        app.errorBox('Registration failed', data_packet['reason'])
    else:
        global CLIENT_NAME, LOGGED_IN
        CLIENT_NAME = data_packet['name']
        LOGGED_IN = True
        app.destroySubWindow('Register login window')

        offers_window()


def register():
    global RQ, CURRENT_ACTION, WAIT_REPLY
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
            WAIT_REPLY.append((RQ, 'REGISTER'))
            s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
            print 'Request: ', request
            CURRENT_ACTION = 'REGISTER'
            RQ += 1
        except socket.error, msg:
            print msg
            app.errorBox('connectionerror', msg)
            server_crash_handling()


def login_failed_handler(data_packet):
    app.errorBox('Login failed', data_packet['reason'])


def login_success_handler(data_packet):
    global CLIENT_NAME, LOGGED_IN
    CLIENT_NAME = data_packet['name']
    LOGGED_IN = True
    app.destroySubWindow('Register login window')

    offers_window()


def login():
    global RQ, CURRENT_ACTION
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
            WAIT_REPLY.append((RQ, 'LOGIN'))
            s.sendto(cPickle.dumps(request), (SERVER_IP, SERVER_PORT))
            print 'Request: ', request
            CURRENT_ACTION = 'LOGIN'
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
    'DEREG-DENIED': dereg_handler,
    'DEREG-CONF': dereg_handler,
    'NEW-ITEM': new_item_handler,
    'ITEM-LIST': refresh_offers_list,
    'OFFER-DENIED': offer_response_handler,
    'OFFER-CONF': offer_response_handler,
    'LOGOUT-DENIED': 0,
    'LOGOUT-CONF': 0,
    'SOLD-TO': 0,
    'NOT-SOLD': 0
}


def action_dispatcher(data_packet):
    action = data_packet['message-type']
    print 'Received reply:'
    print action, data_packet
    ACTION_LIST[action](data_packet)


def msgHandlerCallback(success):
    if not success:
        app.errorBox('','Server connection is corrupted')
        server_crash_handling()
        app.stop()
        s.close()
        sys.exit(1)


# UDP listener
def msgHandler():
    global msgQueue, REGISTER_WINDOW_UP, WAIT_REPLY
    print 'HERE AT MSGHANDLER'
    try:
        while 1:
            message = msgQueue.get()
            if message is None:
                print 'here'
                # print len(WAIT_REPLY)
                if len(WAIT_REPLY) != 0:
                    print 'wait reply list is not empty'
                    raise socket.error
                continue
            else:
                data_packet = cPickle.loads(message[0])
                if data_packet['message-type'] not in REACTION_LIST[WAIT_REPLY[0]]:
                    raise socket.error
                else:
                    WAIT_REPLY.pop(0)
                    app.queueFunction(action_dispatcher, data_packet)
    except KeyboardInterrupt:
        print "Keyboard interrupt"
    except socket.error as e:
        print e.message
    finally:
        print "client shut down"

        return False


def connect():
    port = int(app.getEntry('Server port'))
    ip = app.getEntry('Server ip')
    print ip, port
    try:
        host = ip
        message = 'CONNECT'
        s.sendto(cPickle.dumps(message), (host, port))
        # print 'line24'
        d = s.recvfrom(MAX_SIZE)
        reply = d[0]
        addr = d[1]
        # reply = msgQueue.get()[0]
        print reply
        if reply == 'OK':
            global SERVER_PORT, SERVER_IP
            SERVER_PORT = port
            SERVER_IP = ip

            # UDP listener starts here
            UDPListener.start()
            app.threadCallback(msgHandler, msgHandlerCallback)

            register_window()

        else:
            app.errorBox('error', 'Connection to server cannot be established')
    except socket.error, msg:
        print msg
        app.errorBox('connectionerror', msg)
        # app.stop()
        # s.close()
        # sys.exit()


def initiate(ip, port):
    initiation_complete = 'Initiation complete, your address: ' + ip + ', ' + str(port[1])
    print initiation_complete

    # app.startSubWindow('Initiation window', stopfunc=checkStop)
    app.startSubWindow('Initiation window', stopfunc=checkStop)

    app.addLabel('initiate', text=initiation_complete)
    """Try to connect to UDP server"""
    app.addLabel('serverconnection', text='Please enter the server port number to establish connection')
    app.addLabel('l34', 'Enter server IP:')
    app.addEntry('Server ip')
    app.setEntry('Server ip', text=ip)
    app.addLabel('l2342', 'Enter server port:')
    app.addNumericEntry('Server port')
    app.setEntry('Server port', 8888)
    app.setEntryMaxLength('Server port', 5)
    app.addButton('server_connect', connect)
    app.stopSubWindow()

    app.startSubWindow('Register login window', stopfunc=checkStop)
    app.addLabel('instruction', text='Please log in or register with your unique name id and server port')
    app.addLabelEntry('Bidding IP')
    app.setEntry('Bidding IP', text=socket.gethostbyname(socket.gethostname()))
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

        initiate(client_ip, client_port)
    except socket.error:
        print "Failed to create socket"
        app.errorBox('initiate', 'Failed to create socket')
        app.go()
        sys.exit(1)

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
