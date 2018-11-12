import sqlite3


class dbHandler:
    """All db manipulations"""

    def __init__(self):
        self.CONN = sqlite3.connect('test.db')
        self.CURSOR = self.CONN.cursor()

        self.CURSOR.execute("""CREATE TABLE IF NOT EXISTS users(name VARCHAR primary key , IP VARCHAR , socket INTEGER )""")
        self.CURSOR.execute("""CREATE TABLE IF NOT EXISTS offers(ID INTEGER PRIMARY KEY autoincrement , name VARCHAR NOT NULL, description VARCHAR , IP VARCHAR , minimum INTEGER , finished BIT DEFAULT 0, t TIMESTAMP DEFAULT CURRENT_TIMESTAMP, winnername VARCHAR DEFAULT 'NONE', finalprice INTEGER DEFAULT 0)""")
        self.CURSOR.execute("""CREATE TABLE IF NOT EXISTS biddings(ID INTEGER PRIMARY KEY AUTOINCREMENT , itemID INTEGER, biddername VARCHAR, amount INTEGER, t TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        # biddings(itemID)=offers(ID), biddings(biddername)=users(name)
        self.CONN.commit()

    def get_cursor(self):
        return self.CURSOR

    def register(self, name, ip, socket):
        try:
            self.CURSOR.execute("""INSERT INTO users(name, IP, socket) VALUES(?, ?, ?)""", (name, ip, socket))
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message  # will trigger error if user is already registered
        return True

    def is_registered(self, name):
        # assume that no user will use duplicated IP address when registering
        result = self.CURSOR.execute("""SELECT * FROM users WHERE name = ?""", (name,)).fetchall()
        return len(result) != 0

    def deregister(self, name):
        try:
            self.CURSOR.execute("""DELETE FROM users WHERE name=?""", (name,))
            self.CURSOR.execute("""DELETE FROM offers WHERE name=? AND finished=FALSE""", (name,))
            # assume that bidding of deregistered user's offers continue
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message
        return True

    def user_offer_already_exists(self, name, description):
        result = self.CURSOR.execute("""SELECT * FROM offers WHERE name=? AND description=?""", (name, description)).fetchall()
        return len(result) != 0

    def offer_exists(self, itemID):
        result = self.CURSOR.execute("""SELECT * FROM offers WHERE ID=?""", (itemID,)).fetchall()
        return len(result) != 0

    def get_user_offers(self, name):
        return self.CURSOR.execute("""SELECT * FROM offers WHERE name=?""", (name,)).fetchall()

    def new_offer(self, name, description, ip, minimum):
        if not self.is_registered(name):
            return False, "User %s is not registered" % name
        if self.user_offer_already_exists(name, description):
            return False, "User %s already made the offer %s" % (name, description)
        user_current_offers = self.CURSOR.execute("""SELECT COUNT(*) FROM offers WHERE name=? AND finished=0""", (name,)).fetchall()
        # print user_current_offers[0][0]
        if user_current_offers[0][0] > 2:
            # print user_current_offers
            return False, "User %s already has 3 currently active offers" % name
        try:
            self.CURSOR.execute("""INSERT INTO offers(name, description, IP, minimum) VALUES (?,?,?,?)""", (name, description, ip, minimum))
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message
        return True

    def all_offers(self):
        return self.CURSOR.execute("""SELECT * FROM main.offers""").fetchall()

    def offer_isfinished(self, itemID):
        return self.CURSOR.execute("""SELECT finished FROM offers WHERE ID=?""", (itemID,)).fetchone()[0]

    def get_offer_time(self, itemID):
        result = self.CURSOR.execute("""SELECT t FROM offers WHERE ID=?""", (itemID,)).fetchone()
        if result is None:
            return False, "Offer %s does not exist" % itemID
        return result[0]

    def new_bidding(self, itemID, biddername, amount):
        # assume that same user can bid on the same item as many times as he likes
        # also assume that the previous owner of the item can bid on his offered item
        if not self.is_registered(biddername):
            return False, "User %s is not registered for bidding" % biddername
        if not self.offer_exists(itemID):
            return False, "Offer %s does not exist" % itemID
        if self.offer_isfinished(itemID):
            return False, "Cannot place bid, item %s has finished bidding"

        current_highest = self.CURSOR.execute("""SELECT MAX(amount) FROM biddings WHERE itemID =?""", (itemID,)).fetchone()[0]

        if current_highest is not None and amount <= current_highest:
            return False, "Need to bid higher than %s" % current_highest
        try:
            self.CURSOR.execute("""INSERT INTO biddings(itemID, biddername, amount) VALUES(?,?,?)""", (itemID, biddername, amount))
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message
        return True

    def highest_bidding(self, offer_itemID):
        offer_look = self.CURSOR.execute("""SELECT * FROM offers WHERE ID=?""", (offer_itemID,)).fetchone()
        if offer_look is None:
            return False, "Offer %s does not exist" % offer_itemID
        result = self.CURSOR.execute("""SELECT biddername, MAX(amount) FROM biddings WHERE itemID=?""", (offer_itemID,)).fetchone()
        if result is None:
            return False, "No one has bid on %s" % offer_itemID  # todo or return 0
        return result

    def close_bidding(self, itemID):
        winner = self.highest_bidding(itemID)
        if winner[0] is False:
            return winner
        try:
            self.CURSOR.execute("""UPDATE offers SET finished=1, winnername=?, finalprice=? WHERE ID=?""", (winner[0], winner[1], itemID))
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message

        offerer_name = self.CURSOR.execute("""SELECT name FROM offers WHERE ID=?""", (itemID,)).fetchone()[0]
        return True, (offerer_name, winner[1])  # returns the offerer name and the final price of the item

    def close(self):
        self.CONN.close()


if __name__ == "__main__":
    handler = dbHandler()
    print handler.register('nobody', '127.0.1.5', 12345)
    print handler.new_offer('nobody', 'another vase', '1234679', 2)
    print handler.new_offer('nobody', 'yet another vase', '1234679', 2)
    print handler.new_offer('nobody', 'vase', '1234679', 2)
    print handler.new_offer('nobody', 'number 4 vase', '1234679', 2)
    print handler.all_offers()
    print handler.offer_isfinished(2)
    print handler.get_offer_time(2)

    print handler.new_bidding(3, 'nobody', 6)
    print handler.new_bidding(3, 'nobody', 6)
    print handler.new_bidding(3, '???', 6)
    print handler.new_bidding(333, 'nobody', 6)
    print handler.new_bidding(3, 'nobody', 8)
    print handler.register('new guy', '127.0.1.5', 12345)
    print handler.new_bidding(3, 'new guy', 88)
    print handler.highest_bidding(3)
    print handler.close_bidding(3)
    handler.close()
