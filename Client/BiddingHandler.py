import threading
import Queue
from .TCPClient import TCPClient


class BiddingHandler (threading.Thread):
    def __init__(self, HOST, PORT, minimumBid):
        super(BiddingHandler, self).__init__()
        self.msgQueue = Queue.Queue()
        self.tcpclient = TCPClient(self.msgQueue, self.HOST, self.PORT)
        self.tcpclient.start()
        self.biddingClosed = threading.Event()

    def run(self):
        while not biddingClosed.isSet():
            msg = self.msgQueue.get()
            
