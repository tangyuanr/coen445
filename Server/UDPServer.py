#! /usr/bin/python

import Queue
import threading
import socket
import sys
import cPickle
from Server.dbHandler.dbHandler import dbHandler
from Server.Item import Item

__MAXSIZE__ = 65535




class UDPServer:
    """docstring for UDPServer."""

    def __init__(self, HOST, PORT, msgQueue, MAXSIZE=__MAXSIZE__):
        self.HOST = HOST
        self.PORT = PORT
        self.killFlag = threading.Event()
        self.recvQueue = msgQueue
        self.DBHANDLER = dbHandler()
        self.client_ip_list = {}
        self.OFFER_BROADCAST_INTERVAL = 10.0
        self.PREVIOUS_ACTIVE_OFFERS = self.DBHANDLER.get_all_active_offers()
        self.OFFER_COUNT = len(self.PREVIOUS_ACTIVE_OFFERS)

        self.ACTION_LIST = {
            'REGISTER': self.register,
            'DEREGISTER': self.deregister,
            'OFFER': self.offer,
            'LOGIN': self.login,
            'GET-ITEMS': self.get_items,
            'LOGOUT': self.logout
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
            print 'SERVER ADDRESS: '
            print self.sckt.getsockname()
            print socket.gethostbyname(socket.gethostname())
        except socket.error, msg:
            print >> sys.stderr, 'Bind failed. Error Code : ' + str(msg[0]) \
                                 + ' Message ' + msg[1]
            raise

        self.UDPRcvr = UDPReceive('UDPRcvr', self.killFlag,
                                  self.sckt, self.recvQueue)
        self.UDPRcvr.start()

        # restart unfinished offers
        if len(self.PREVIOUS_ACTIVE_OFFERS) != 0:
            print 'Restarting unfinished offers'
            self.update_offer_port_after_restart(self.PREVIOUS_ACTIVE_OFFERS)

    def offers_broadcast(self):  # unused
        threading.Timer(self.OFFER_BROADCAST_INTERVAL, self.offers_broadcast).start()
        # print 'im the offer broadcaster', len(self.client_ip_list), self.OFFER_COUNT

        # self.offers_broadcast_thread.daemon = True
        # self.offers_broadcast_thread.start()

        if len(self.client_ip_list) != 0:
            # print "client list not empty"
            if self.OFFER_COUNT != 0:
                # print 'offers not empty'
                db = dbHandler()
                offers = db.get_all_active_offers()
                response = {
                    'message-type': 'OFFER-BROADCAST',
                    'offers': offers
                }
                for client in self.client_ip_list:
                    print client, response
                    self.send(cPickle.dumps(response), self.client_ip_list[client])

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
        print "***************Registration***************"
        sender_ip, sender_port = sender_info
        sender_name = data_packet['name']
        RQ = data_packet['RQ']
        status = self.DBHANDLER.register(sender_name, sender_ip, sender_port)
        if status is not True:
            # Unregister
            reason = status[1]
            print "Registration failed, reason: " + reason
            response = {
                'RQ': RQ,
                'success': False,
                'message-type': 'UNREGISTER',
                'reason': reason
            }
            self.send(cPickle.dumps(response), sender_info)

        else:
            # Registered
            print self.DBHANDLER.get_user_info(sender_name)
            response = {
                'RQ': RQ,
                'success': True,
                'message-type': 'REGISTERED',
                'name': sender_name,
                'ip': sender_ip,
                'port': sender_port
            }
            self.send(cPickle.dumps(response), sender_info)
            self.client_ip_list[sender_name] = sender_info
        print 'Response: ', response

    def login(self, sender_info, data_packet):
        print "***************LOGIN**************************"
        sender_name = data_packet['name']
        RQ = data_packet['RQ']
        sender_ip, sender_port = sender_info
        if not self.DBHANDLER.is_registered(sender_name):
            response = {
                'RQ': RQ,
                'success': False,
                'message-type': 'LOGIN-FAILED',
                'reason': 'User not registered'
            }
            self.send(cPickle.dumps(response), sender_info)
        else:
            status = self.DBHANDLER.update_user_address(sender_name, sender_ip, sender_port)
            if status is not True:
                response = {
                    'RQ': RQ,
                    'success': False,
                    'message-type': 'LOGIN-FAILED',
                    'reason': status[1]
                }
                self.send(cPickle.dumps(response), sender_info)
            else:
                response = {
                    'RQ': RQ,
                    'success': True,
                    'message-type': 'LOGIN-CONF',
                    'name': sender_name
                }
                self.send(cPickle.dumps(response), sender_info)
                self.client_ip_list[sender_name] = sender_info
        print 'Response: ', response

    def deregister(self, sender_info, data_packet):
        # this should be an idempotent function, return true unless the db malfunctions
        print "***************DEREGISTRATION******************"
        sender_name = data_packet['name']
        RQ = data_packet['RQ']

        status = self.DBHANDLER.deregister(sender_name)
        if status is not True:
            response = {
                'RQ': RQ,
                'success': False,
                'message-type': 'DEREG-DENIED',
                'reason': status[1]
            }
            self.send(cPickle.dumps(response), sender_info)
        else:
            response = {
                'RQ': RQ,
                'success': True,
                'message-type': 'DEREG-CONF'
            }
            self.send(cPickle.dumps(response), sender_info)
        print 'Response:', response

    def update_offer_port_after_restart(self, offers):
        for offer in offers:
            owner_name = offer[1]
            owner_ip = offer[3]
            owner_port = self.DBHANDLER.get_user_info(owner_name)[2]
            if owner_port is None:
                print "Owner of the offer " + offer[0] + " is no longer registered"
                continue
            port = self.new_item(offer[0], offer[2], offer[5], (owner_name, (owner_ip, owner_port)))

            status = self.DBHANDLER.update_offer_port(offer[0], port)
            if status is not True:
                print status[1]

    def new_item(self, item_id, description, minimum, ownerdetail):
        print '******************NEW-ITEM********************'
        new_bidding_item = Item(item_id, description, minimum, ownerdetail, self.sckt)
        new_bidding_item.start()
        bidding_port = new_bidding_item.server.getSocketAddress()[1]
        # TODO: update offer port after started bidding TCP server
        response = {
            'message-type': 'NEW-ITEM',
            'item-id': item_id,
            'description': description,
            'minimum': minimum,
            'port': bidding_port
        }

        for client in self.client_ip_list:
            self.send(cPickle.dumps(response), self.client_ip_list[client])
            print 'Client: ', self.client_ip_list[client], 'Response: ', response
        return bidding_port

    def get_items(self, sender_info, data_packet):  # TODO: select active offers only
        print '*****************GET-ITEMS*******************'
        items = self.DBHANDLER.all_offers()
        response = {
            'RQ': data_packet['RQ'],
            'success': True,
            'message-type': 'ITEM-LIST',
            'items': items
        }
        self.send(cPickle.dumps(response), sender_info)
        print 'Response: ', response

    def offer(self, sender_info, data_packet):
        print "********************OFFER**********************"
        sender_ip = sender_info[0]
        RQ = data_packet['RQ']
        sender_name = data_packet['name']
        description = data_packet['description']
        minimum = data_packet['minimum']
        status = self.DBHANDLER.new_offer(sender_name, description, sender_ip, minimum)
        self.OFFER_COUNT += 1

        if status[0] is not True:
            response = {
                'RQ': RQ,
                'success': False,
                'message-type': 'OFFER-DENIED',
                'reason': status[1]
            }
            self.send(cPickle.dumps(response), sender_info)
            # TODO: call new_item()
        else:
            response = {
                'RQ': RQ,
                'success': True,
                'message-type': 'OFFER-CONF',
                'item-id': status[1],
                'description': status[2],
                'minimum': status[3]
            }
            self.send(cPickle.dumps(response), sender_info)
            self.new_item(status[0], status[1], status[2], (sender_name, sender_info))
        print 'Response: ', response

    def logout(self, sender_info, data_packet):
        print "****************LOGOUT****************"
        sender_ip = sender_info[0]
        RQ = data_packet['RQ']
        sender_name = data_packet['name']

        status = self.DBHANDLER.user_isactive(sender_name)
        if status is not False:
            response = {
                'RQ': RQ,
                'message-type': 'LOGOUT-DENIED',
                'reason': status[1]
            }
            self.send(cPickle.dumps(response), sender_info)
        else:
            try:
                self.client_ip_list.pop(sender_name)
            except KeyError:
                pass  # client is somehow already gone, good riddance
            response = {
                'RQ': RQ,
                'message-type': 'LOGOUT-CONF',
                'success': True
            }
            self.send(cPickle.dumps(response), sender_ip)

    def receive(self, message):
        print '\nReception:'
        sender_info = message[1]
        print "sender info: ", sender_info
        data_packet = cPickle.loads(message[0])
        print "data packet ", data_packet

        if data_packet == 'CONNECT':
            print "Received connection request"
            self.send('OK', sender_info)
        else:
            try:
                self.ACTION_LIST[data_packet['message-type']](sender_info, data_packet)
            except KeyError:
                print "Request does not exist"


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
        # udpserver.offers_broadcast()
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
                # print udpserver.client_ip_list
                # print "Received message from: " + str(msg[1])
                # print cPickle.loads(msg[0])
                # print "Sending reply."
                # toSend = "You sent: " + msg[0]
                # udpserver.send(toSend, msg[1])
    except KeyboardInterrupt:
        print "Ctrl-C detected!"
    except socket.error:
        raise
    finally:
        print "Shutting down UDP Server."
        udpserver.shutdown()

    sys.exit(0)
