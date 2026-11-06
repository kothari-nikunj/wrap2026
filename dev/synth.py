"""Build a tiny made-up chat.db + AddressBook for tests. No real data."""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

COCOA = 978307200
UTC = timezone.utc

CHAT_SCHEMA = """
CREATE TABLE message(ROWID INTEGER PRIMARY KEY, text TEXT, handle_id INT, is_from_me INT, date INT,
  destination_caller_id TEXT, associated_message_type INT DEFAULT 0, cache_has_attachments INT DEFAULT 0,
  item_type INT DEFAULT 0);
CREATE TABLE handle(ROWID INTEGER PRIMARY KEY, id TEXT, service TEXT);
CREATE TABLE chat(ROWID INTEGER PRIMARY KEY, display_name TEXT, account_login TEXT, chat_identifier TEXT, style INT);
CREATE TABLE chat_handle_join(chat_id INT, handle_id INT);
CREATE TABLE chat_message_join(chat_id INT, message_id INT);
"""

AB_SCHEMA = """
CREATE TABLE ZABCDRECORD(ROWID INTEGER PRIMARY KEY, Z_PK INT, ZFIRSTNAME TEXT, ZLASTNAME TEXT,
  ZORGANIZATION TEXT, ZNICKNAME TEXT);
CREATE TABLE ZABCDPHONENUMBER(ZOWNER INT, ZFULLNUMBER TEXT);
CREATE TABLE ZABCDEMAILADDRESS(ZOWNER INT, ZADDRESS TEXT);
"""


class ChatDB:
    """chat.db with 1:1 chats and group chats. Times are aware datetimes."""

    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(CHAT_SCHEMA)
        self.next_id = 0

    def handle(self, rowid, handle_id):
        self.conn.execute('INSERT INTO handle VALUES(?,?,?)', (rowid, handle_id, 'iMessage'))

    def chat(self, rowid, handles, group=False, name=None):
        self.conn.execute('INSERT INTO chat VALUES(?,?,NULL,?,?)', (rowid, name, f'c{rowid}', 43 if group else 45))
        for h in handles:
            self.conn.execute('INSERT INTO chat_handle_join VALUES(?,?)', (rowid, h))

    def message(self, chat, handle, from_me, when, text='hi there'):
        self.next_id += 1
        ns = int((when.timestamp() - COCOA) * 1e9)
        self.conn.execute('INSERT INTO message VALUES(?,?,?,?,?,NULL,0,0,0)',
                          (self.next_id, text, handle, int(from_me), ns))
        self.conn.execute('INSERT INTO chat_message_join VALUES(?,?)', (chat, self.next_id))

    def daily(self, chat, handle, start, days, per_day, from_me=lambda k: k % 2):
        for day in range(days):
            for k in range(per_day):
                self.message(chat, handle, from_me(k), start + timedelta(days=day, minutes=7 * k))

    def close(self):
        self.conn.commit()
        self.conn.close()


def address_book(directory, people):
    """people: [(first, last, phones, emails)]"""
    os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(os.path.join(directory, 'AddressBook-v22.abcddb'))
    conn.executescript(AB_SCHEMA)
    for pk, (first, last, phones, emails) in enumerate(people, 1):
        conn.execute('INSERT INTO ZABCDRECORD VALUES(?,?,?,?,NULL,NULL)', (pk, pk, first, last))
        conn.executemany('INSERT INTO ZABCDPHONENUMBER VALUES(?,?)', [(pk, p) for p in phones])
        conn.executemany('INSERT INTO ZABCDEMAILADDRESS VALUES(?,?)', [(pk, e) for e in emails])
    conn.commit()
    conn.close()


def at(y, m, d, hh=12, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


WA_SCHEMA = """
CREATE TABLE ZWACHATSESSION(Z_PK INTEGER PRIMARY KEY, ZCONTACTJID TEXT, ZSESSIONTYPE INT, ZPARTNERNAME TEXT);
CREATE TABLE ZWAMESSAGE(Z_PK INTEGER PRIMARY KEY, ZTEXT TEXT, ZISFROMME INT, ZMESSAGEDATE REAL, ZCHATSESSION INT);
CREATE TABLE ZWAPROFILEPUSHNAME(ZJID TEXT, ZPUSHNAME TEXT);
"""


class WhatsAppDB:
    """WhatsApp ChatStorage.sqlite: sessions (0 = 1:1, 1 = group), messages, push names."""

    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.executescript(WA_SCHEMA)

    def session(self, pk, jid, name=None, group=False):
        self.conn.execute('INSERT INTO ZWACHATSESSION VALUES(?,?,?,?)', (pk, jid, 1 if group else 0, name))
        if name and not group:
            self.conn.execute('INSERT INTO ZWAPROFILEPUSHNAME VALUES(?,?)', (jid, name))

    def message(self, session, from_me, when, text='hi there'):
        self.conn.execute('INSERT INTO ZWAMESSAGE(ZTEXT, ZISFROMME, ZMESSAGEDATE, ZCHATSESSION) VALUES(?,?,?,?)',
                          (text, int(from_me), when.timestamp() - COCOA, session))

    def close(self):
        self.conn.commit()
        self.conn.close()


class CallDB:
    """CallHistory.storedata ZCALLRECORD. call_type: 1 phone, 8 FaceTime audio, 16 FaceTime video."""

    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.execute('CREATE TABLE ZCALLRECORD(Z_PK INTEGER PRIMARY KEY, ZADDRESS TEXT, ZDURATION REAL, ZDATE REAL,'
                          ' ZORIGINATED INT, ZANSWERED INT, ZCALLTYPE INT)')

    def call(self, address, when, duration=120, originated=1, answered=1, call_type=1):
        self.conn.execute('INSERT INTO ZCALLRECORD(ZADDRESS, ZDURATION, ZDATE, ZORIGINATED, ZANSWERED, ZCALLTYPE)'
                          ' VALUES(?,?,?,?,?,?)', (address, duration, when.timestamp() - COCOA, originated, answered, call_type))

    def close(self):
        self.conn.commit()
        self.conn.close()
