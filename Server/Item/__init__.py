import Queue
import threading
from ..TCPServer import TCPServer


class Item (threading.Thread):
    """Holds current item values and TCPServer for client connexion"""

    def __init__(self, itemID, name, minimumBid,
                 owner, dbHandler, timeLeft=300, port=0):
        self.itemID = itemID
        self.name = name
        self.highestBid = minimumBid
        self.owner = owner
        self.highestBidder = owner
        self.recvQueue = Queue.Queue()
        self.dbHandler = dbHandler
        self.timeLeft = timeLeft
        self.server = TCPServer.TCPServer()
        self.biddingClosed = threading.Event()

        def countDown():
            self.timeLeft -= 30
            if self.timLeft <= 0:
                self.closeBidding()
            else:
                self.timer.start()
        self.timer = threading.Timer(30.0, countDown)

    def run(self):
        self.timer.start()
        while not self.biddingClosed.isSet():
            msg = self.recvQueue.get()
            if msg is not None:
                # TODO: check if IP address is registered in DB
                bid = msg[1]
                if bid is not None:
                    itemID = bid[1]["Item"]
                    if itemID == self.itemID:
                        amount = bid[1]["Val"]
                        if amount > self.highestBid:
                            self.highestBid = amount
                            self.highestBidder = bid[0]
                            # TODO: send highest to all

    def closeBidding(self):
        self.biddingClosed.set()
        # TODO: if winner, send win message to winner
        # TODO: send bid-over message to all
        # TODO: send owner sold-to or not-sold message
        self.recvQueue.put(None)
        self.TCPServer.shutdown()


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
