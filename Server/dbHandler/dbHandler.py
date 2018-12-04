import sqlite3


class dbHandler:
    """All db manipulations"""

    def __init__(self):
        self.CONN = sqlite3.connect('test.db')
        self.CURSOR = self.CONN.cursor()

        self.CURSOR.execute("""CREATE TABLE IF NOT EXISTS users(name VARCHAR primary key , IP VARCHAR , 
            socket INTEGER )""")
        self.CURSOR.execute("""CREATE TABLE IF NOT EXISTS offers(ID INTEGER PRIMARY KEY autoincrement , 
            name VARCHAR NOT NULL, description VARCHAR , ownerIP VARCHAR , itemPort INTEGER DEFAULT 50000, 
            minimum UNSIGNED INTEGER , 
            finished BIT DEFAULT 0, timeleft INTEGER DEFAULT 3000, winnername VARCHAR DEFAULT 'NONE', 
            finalprice INTEGER DEFAULT 0)""")
        # self.CURSOR.execute("""CREATE TABLE IF NOT EXISTS biddings(ID INTEGER PRIMARY KEY AUTOINCREMENT ,
        #     itemID INTEGER, biddername VARCHAR, amount INTEGER, t TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
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

    def get_user_info(self, name):
        result = self.CURSOR.execute("""SELECT * FROM users WHERE name = ?""", (name, )).fetchone()
        return result

    def get_user_info_from_ip(self, ip):
        result = self.CURSOR.execute("""SELECT * FROM users WHERE IP=?""", (ip, )).fetchone()
        return result

    def is_registered(self, name):
        # assume that no user will use duplicated IP address when registering
        result = self.CURSOR.execute("""SELECT * FROM users WHERE name = ?""", (name,)).fetchall()
        return len(result) != 0

    def ip_is_registered(self, ip):
        result = self.CURSOR.execute("""SELECT * FROM users WHERE IP=?""", (ip,)).fetchall()
        return len(result) != 0

    def user_ip_match(self, name, ip):
        result = self.CURSOR.execute("""SELECT * FROM users WHERE name=? AND IP=?""", (name, ip)).fetchall()
        if len(result) == 0:
            return False, "User is not logged on the specified bidding address"
        return True

    def update_user_address(self, name, ip, sckt):  # TODO test update user ip and port
        try:
            self.CURSOR.execute("""UPDATE users SET IP=?, socket=? WHERE name=?""", (ip, sckt, name))
        except sqlite3.Error as e:
            return False, e.message
        return True

    def get_all_active_offers(self):
        result = self.CURSOR.execute("""SELECT * FROM offers WHERE finished = 0""").fetchall()
        return result

    def get_user_active_offers(self, name):
        result = self.CURSOR.execute("""SELECT * FROM offers WHERE name = ? AND finished = 0""", (name,)).fetchall()
        return result

    def user_isactive(self, name):
        if len(self.get_user_active_offers(name)) != 0:
            return True, "The auction for your offer(s) is not finished. Please wait until the end or cancel your offer(s)."
        active = name in self.CURSOR.execute("""SELECT * FROM offers WHERE winnername=?""", (name,)).fetchall()
        if active:
            return True, "The auction for the item(s) you have placed bids is not finished. Please wait until the end."
        return False

    def deregister(self, name):
        if len(self.get_user_active_offers(name)) != 0:
            return False, "The auction for your offer(s) is not finished. Please wait until the end or cancel your offer(s)."
        active = name in self.CURSOR.execute("""SELECT * FROM offers WHERE winnername=?""", (name,)).fetchall()
        if active:
            return False, "The auction for the item(s) you have placed bids is not finished. Please wait until the end."
        try:
            self.CURSOR.execute("""DELETE FROM users WHERE name=?""", (name,))
            self.CURSOR.execute("""DELETE FROM offers WHERE name=? AND finished=0""", (name,))
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
            self.CURSOR.execute("""INSERT INTO offers(name, description, ownerIP, minimum) VALUES (?,?,?,?)""", (name, description, ip, minimum))
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message
        offer_id = self.CURSOR.execute("""SELECT ID FROM offers WHERE description=? AND name=?""", (description, name)).fetchone()
        return True, offer_id[0], description, minimum

    def all_offers(self):
        return self.CURSOR.execute("""SELECT * FROM main.offers""").fetchall()

    def offer_isfinished(self, itemID):
        return self.CURSOR.execute("""SELECT finished FROM offers WHERE ID=?""", (itemID,)).fetchone()[0]

    def get_offer_time_left(self, itemID):
        result = self.CURSOR.execute("""SELECT timeleft FROM offers WHERE ID=?""", (itemID,)).fetchone()
        if result is None:
            return False, "Offer %s does not exist" % itemID
        return result[0]

    def update_offer_port(self, itemID, itemPort):
        try:
            self.CURSOR.execute("""UPDATE offers SET itemPort=? WHERE ID=?""", (itemPort,itemID))
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message
        return True

    """Item related functions"""
    def update_offer_time_left(self, itemID, timeleft):
        try:
            self.CURSOR.execute("""UPDATE offers SET timeleft=? WHERE ID=?""", (timeleft,itemID))
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message
        return True

    def new_bidding(self, itemID, biddername, amount):
        # assume that same user can bid on the same item as many times as he likes
        # also assume that the previous owner of the item can bid on his offered item
        try:
            self.CURSOR.execute("""UPDATE offers SET finalprice=?, winnername=? WHERE ID=?""", (amount, biddername, itemID))
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message
        return True

    def highest_bidding(self, offer_itemID):
        result = self.CURSOR.execute("""SELECT winnername, finalprice FROM offers WHERE ID=?""", (offer_itemID,)).fetchone()
        return result

    def close_bidding(self, itemID):
        winner = self.highest_bidding(itemID)
        if winner[0] is False:
            return winner
        try:
            self.CURSOR.execute("""UPDATE offers SET finished=1 WHERE ID=?""", (itemID,))
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
    # print handler.offer_isfinished(2)
    # print handler.get_offer_time(2)

    print handler.new_bidding(3, 'nobody', 6)
    print handler.new_bidding(3, 'nobody', 6)
    print handler.new_bidding(3, '???', 6)
    print handler.new_bidding(333, 'nobody', 6)
    print handler.new_bidding(3, 'nobody', 8)
    print handler.register('new guy', '127.0.1.5', 12345)
    print handler.new_bidding(3, 'new guy', 88)
    print handler.highest_bidding(3)
    # print handler.close_bidding(3)
    print handler.get_user_active_offers('nobody')
    # print handler.get_user_active_biddings('nobody')
    # cur = handler.get_cursor()
    # cur.execute("""SELECT * FROM offers INNER JOIN biddings ON offers.ID = biddings.itemID""", ("nobody", )).fetchall()
    print handler.all_offers()
    print "HERE"
    print handler.get_user_info_from_ip('123156')
    handler.close()
