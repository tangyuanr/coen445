from appJar import gui


class Bidding:

    def __init__(self, offer_info, client_name, client_ip):
        self.item_id = offer_info[0]
        self.ownername = offer_info[1]
        self.description = offer_info[2]
        self.ownerIP = offer_info[3]
        self.item_port = offer_info[4]
        self.minimum = offer_info[5]
        self.finished = offer_info[6]
        self.timeleft = offer_info[7]
        self.winnername = offer_info[8]
        self.finalprice = offer_info[9]
        self.client_name = client_name
        self.client_ip = client_ip

        self.app = gui('Bidding for item ' + str(self.item_id))
        self.app.startSubWindow('Bidding for item ' + str(self.item_id), stopfunc=self.checkStop)
        self.app.addLabel('l1', 'Item ID: ', row=0, column=0)
        self.app.addLabel('Item ID', self.item_id, row=0, column=1)
        self.app.addLabel('l2', 'Description: ', row=1, column=0)
        self.app.addLabel('Description', self.description, row=1, column=1)
        self.app.addLabel('l3', 'Minimum: ', row=2, column=0)
        self.app.addLabel('Minimum', self.minimum, row=2, column=1)
        self.app.addLabel('l4', 'Time left: ', row=3, column=0)
        self.app.addLabel('Time left', self.timeleft, row=3, column=1)
        self.app.addLabel('l5', 'Current highest', row=4, column=0)
        self.app.addLabel('Current highest', self.finalprice, row=4, column=1)
        self.app.stopSubWindow()

        self.app.go()

    def start(self):
        self.app.go()
        # make first connection attempt with server
        # then start the handler thread
        # self.app.thread(handler)

    def checkStop(self):
        pass  # TODO: ask server if it's ok to quit

    def stop(self):
        self.app.stop()
