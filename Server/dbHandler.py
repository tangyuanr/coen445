import sqlite3


class dbHandler:
    """All db manipulations"""

    def __init__(self):
        self.CONN = sqlite3.connect('test.db')
        self.CURSOR = self.CONN.cursor()

        self.CURSOR.execute("""CREATE TABLE IF NOT EXISTS users(name VARCHAR primary key , IP VARCHAR , socket INTEGER )""")
        self.CURSOR.execute("""CREATE TABLE IF NOT EXISTS offers(ID INTEGER PRIMARY KEY autoincrement , name VARCHAR NOT NULL, description VARCHAR , IP VARCHAR , minimum INTEGER , finished BIT DEFAULT 0, t TIMESTAMP DEFAULT CURRENT_TIMESTAMP, winnername VARCHAR DEFAULT 'NONE')""")
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

    def offer_exists(self, name, description):
        result = self.CURSOR.execute("""SELECT * FROM offers WHERE name=? AND description=?""", (name, description)).fetchall()
        return len(result) != 0

    def get_user_offers(self, name):
        return self.CURSOR.execute("""SELECT * FROM offers WHERE name=?""", (name,)).fetchall()

    def new_offer(self, name, description, ip, minimum):
        if not self.is_registered(name):
            return False, "User %s is not registered" % name
        if self.offer_exists(name, description):
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

    def new_bidding(self, itemID, biddername, amount):
        if not self.is_registered(biddername):
            return False, "User %s is not registered for bidding" % biddername
        if self.offer_isfinished(itemID):
            return False, "Cannot place bid, item %s has finished bidding"

        try:
            self.CURSOR.execute("""INSERT INTO biddings(itemID, biddername, amount) VALUES(?,?,?)""", (itemID, biddername, amount))
            self.CONN.commit()
        except sqlite3.Error as e:
            return False, e.message
        return True

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
    handler.close()
