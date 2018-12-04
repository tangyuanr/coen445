import Queue
import threading
import cPickle
from Server.TCPServer import TCPServer
from Server.dbHandler.dbHandler import dbHandler


class Item (threading.Thread):
    """Holds current item values and TCPServer for client connexion"""

    def __init__(self, itemID, name, minimumBid,
                 owner, socket, highestBidder=None, timeLeft=300, port=0):
        super(Item, self).__init__()
        self.itemID = itemID
        self.name = name
        self.highestBid = minimumBid
        self.owner = owner
        self.udpSocket = socket
        self.timeLeft = timeLeft
        self.recvQueue = Queue.Queue()
        self.server = TCPServer(self.recvQueue)
        self.biddingClosed = threading.Event()
        self.highestBidder = None
        handler = dbHandler()
        handler.update_offer_port(itemID, self.server.getSocketAddress()[1])
        if highestBidder is not None:
            self.highestBidder = handler.get_user_info(highestBidder)
        handler.close()

        def countDown():
            if not self.biddingClosed.set():
                self.timeLeft -= 30
                if self.timeLeft <= 0:
                    self.closeBidding()
                else:
                    handler = dbHandler()
                    handler.update_offer_time_left(itemID, self.timeLeft)
                    handler.close()
                    self.timer.start()

        self.timer = threading.Timer(30.0, countDown)

    def run(self):
        self.timer.start()
        while not self.biddingClosed.isSet():
            handler = dbHandler()
            msg = self.recvQueue.get()
            if msg is not None:

                bid = msg[2]
                if bid is not None:
                    itemID = bid["Item"]
                    if itemID == self.itemID:
                        amount = bid["Val"]
                        if amount > self.highestBid:
                            self.highestBid = amount
                            self.highestBidder = msg[1]
                            handler.new_bidding(itemID, )
                            highestMSG = {
                                "T": "HI",
                                "ID": itemID,
                                "AMT": amount
                            }
                            self.server.sendall(cPickle.dumps(highestMSG, -1))

    def closeBidding(self):
        self.biddingClosed.set()
        handler = dbHandler()
        handler.close_bidding(self.itemID)
        if self.highestBidder is not None:
            win = {
                "T": "WIN",
                "ID": self.itemID,
                "NM": self.owner[1],
                "IP": self.owner[1][0],
                "PRT": self.owner[1][1],
                "AMT": self.minimumBid
            }
            self.highestBidder[0].send(cPickle.dumps(win, -1))
            soldto = {
                "message-type": "soldto",
                "id": self.itemID,
                "name": self.highestBidder[1][0],
                "ip": self.highestBidder[1][1],
                "port": self.highestBidder[0].getRemoteAddress()[1],
                "amount": self.minimumBid
            }
            self.udpSocket.send(cPickle.dumps(soldto, -1), self.owner[1])
        else:
            notsold = {
                "message-type": "notsold",
                "id": self.itemID,
                "reason": "No valid bids"
            }
            self.udpSocket.send(cPickle.dumps(notsold, -1), self.owner[1])

        bidover = {
            "T": "BOV",
            "ID": self.itemID,
            "AMT": self.minimumBid
        }

        self.TCPServer.sendall(cPickle.dumps(bidover, -1))
        self.recvQueue.put(None)
        self.server.shutdown()


if __name__ == '__main__':
    itemID = 99
    name = "Beautifulest Object"
    minimumBid = 100
    HOST = ''
    PORT = 8888
    item = Item(itemID, name, minimumBid, HOST, PORT)
    itemThread = item.start()
    print "Connection open on " + str(item.TCPServer.getSocketAddress())

    try:
        while True:
            item.join()
    except KeyboardInterrupt:
        item.closeBidding()
