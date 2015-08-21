import os
import json
import random
import requests

from config import Config


import sqlite3


class bot:
    bot_username = Config.bot_username
    bot_token = Config.bot_token
    admin_id = Config.admin_id
    help_text = Config.help_text
    settins_text = Config.settings_text
    pause_text = Config.pause_text
    continue_text = Config.continue_text

    chats = {}

    emoji_oh = '😱'
    emoji_silent = '😁'
    emoji_earth_wireframe = '🌐'
    emoji_number = '#⃣'

    def sqlite_execute(self, query, name, debug = False):
        try:
            self.c.execute(query)
            self.conn.commit()
            print ('{0} applied'.format(name))
            return True
        except sqlite3.OperationalError:
            print ('{0} already applied'.format(name))
            if debug:
                raise
            return False
        except:
            raise

    def __init__ (self):
        self.conn = sqlite3.connect('database/instagrambot.db')
        self.c = self.conn.cursor()
        
        exe = self.sqlite_execute('''CREATE TABLE settings
                         (id integer primary key, name text, value text)''', "settings")
        if exe:
            self.c.execute("INSERT INTO settings VALUES (1,'last_update','0')")
        
        self.sqlite_execute('''CREATE TABLE pictures
                         (id text primary key)''', "pictures")
        
        self.sqlite_execute('''CREATE TABLE chats
                         (id integer primary key, lenght integer, last_picture text, last_picture_datetime integer, subscribed integer default 1)''', "chats")
        
        self.sqlite_execute('''CREATE TABLE chat_picture
                         (chat_id integer, picture_id integer, count integer default 1, success integer default 0)''',
                         "chat_message")

        self.sqlite_execute('''CREATE UNIQUE INDEX chat_picture_index
                            on chat_picture (chat_id, picture_id);''', "chat_picture_index")

        # We can also close the connection if we are done with it.
        # Just be sure any changes have been committed or they will be lost.
        #conn.close()

    def send_to_bot(self, access_point, data=None):
        try:
            r = requests.get('https://api.telegram.org/bot{0}/{1}'.format(self.bot_token, access_point), data=data, timeout=40)
        except requests.exceptions.ConnectionError:
            print ("Connection Error")
            return None
        except requests.exceptions.Timeout:
            print ("Connection Timeout")
            return None
        return r

    def get_last_update(self):
        settings = self.c.execute('SELECT * FROM settings WHERE id=1')
        last_update = settings.fetchone()[2]
        #print (last_update)
        return int(last_update)


    def set_last_update(self, number):
        number = '{0}'.format(number)
        self.c.execute("UPDATE settings SET value=? WHERE id=1", (number,))
        self.conn.commit()


    def add_picture(self, picture_id, user_id):
        if user_id != self.admin_id:
            print ('Forbidden')
            return False
        self.c.execute("INSERT INTO pictures (id) VALUES (?);", (picture_id,))
        self.conn.commit()

    def get_picture(self, chat_id):
        pictures = self.c.execute("SELECT * FROM pictures;")
        pictures = pictures.fetchall()
        chat_picture = self.c.execute("SELECT * FROM chat_picture WHERE chat_id=? ORDER BY count ASC;", (chat_id,))
        cp = chat_picture.fetchall()

        unseen_pictures = []
        for p in pictures:
            seen = False
            for c in cp:
                #print('c: {0}, p: {1}'.format(c[1], p[0]))
                if c[1] == p[0]: # Matching picture_id
                    seen = True
                    break
            if not seen:
                unseen_pictures.append(p)

        #print (unseen_pictures)
        if len(unseen_pictures) > 0:
            picture = random.choice(unseen_pictures)
            return picture
        elif len(cp) > 0:
            c = cp[0]
            for p in pictures:
                #print('c: {0}, p: {1}'.format(c[1], p[0]))
                if c[1] == p[0]: # Matching message_id
                    return p
            print ('ERROR, no picture or missing picture')
            return None
        else:
            return None

    def chat_picture(self, picture_id, chat_id):
        chat_picture = self.c.execute("SELECT * FROM chat_picture WHERE chat_id=? AND picture_id=?", (chat_id, picture_id))
        cp = chat_picture.fetchone()
        count = 0
        if cp:
            count = cp[2] + 1
            self.c.execute("UPDATE chat_picture SET count=? WHERE chat_id=? AND picture_id=?", (count, chat_id, picture_id))
            self.conn.commit()
        else:
            self.c.execute("INSERT INTO chat_picture (chat_id, picture_id) VALUES (?,?)", (chat_id, picture_id))
            self.conn.commit()


    def add_chat_lenght(self, chat_id):
        chat = self.c.execute("SELECT * FROM chats WHERE id=?", (chat_id,))
        chat = chat.fetchone()
        if not chat:
            self.c.execute("INSERT INTO chats (id, lenght) VALUES (?,?)", (chat_id, 0))
            self.conn.commit()
        else:
            lenght = chat[1]
            self.c.execute("UPDATE chats SET lenght=? WHERE id=?", (lenght+1, chat_id))
            self.conn.commit()
    
    def get_chat_lenght(self, chat_id):
        chat = self.c.execute("SELECT * FROM chats WHERE id=?", (chat_id,))
        chat = chat.fetchone()
        if chat:
            return chat[1]
        else:
            return None
            
    def get_chats_stats(self):
        messages = self.c.execute("SELECT COUNT(*) FROM pictures")
        messages = messages.fetchone()
        msg_count = messages[0]
        chats = self.c.execute("SELECT lenght FROM chats")
        chats = chats.fetchall()
        if chats:
            average_lenght = 0.0
            count = 0
            ratio = 0
            for chat in chats:
                count += chat[0]
                if chat[0]>0:
                    if chat[0] > msg_count:
                        ratio += 1.0
                    else:
                        ratio += chat[0] / msg_count
            if len(chats) > 0:
                average_lenght = count / len(chats)
                average_ratio = ratio / len(chats)
            stats = {
                'count': len(chats),
                'average_lenght': average_lenght,
                'average_ratio': average_ratio,
                'msg_count': msg_count
            }
            return stats
        else:
            return None
    
    def send_msg(self, msgs, chat_id, action=False):
        options = ['¡No puedo detenerme!', '¡Si!', '¡Otra!', '¡Mas fotos!', '¡Maaaaaas!', '¡Quiero ver mas!']
        option = '📷 {0}'.format(random.choice(options))
        keys = [[option]]
        keyboard = {
            "keyboard": keys,
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        for msg in msgs:
            if action:
                data = {
                    'chat_id': chat_id,
                    'action': 'typing'
                }
                r = self.send_to_bot('sendChatAction', data = data)
            data = {
                'chat_id': chat_id,
                'text': msg,
            }
            if len(keys)>0:
                data['reply_markup'] = json.dumps(keyboard)
            r = self.send_to_bot('sendMessage', data = data)
   

    def push_msg(self, msg, chat_id):
        chats = self.c.execute("SELECT id, subscribed FROM chats")
        chats = chats.fetchall()
        if chats:
            for chat in chats:
                if chat[1]: # Subscribed
                    self.send_msg([msg], chat[0], True)


    def pause(self, chat_id, active):
        if active:
            subscription = 0
        else:
            subscription = 1
        chat = self.c.execute("SELECT id FROM chats WHERE id=?;", (chat_id,))
        chat = chat.fetchone()
        if chat:
            self.c.execute("UPDATE chats SET subscribed=? WHERE id=?;", (subscription, chat_id))
        else:
            self.c.execute("INSERT INTO chats (id, lenght, subscribed) VALUES (?,0,?)", (chat_id, subscription))
        self.conn.commit()


    def bot_loop(self):
        while 1:
            # Send messages
            #users_db = self.db_users.find()
            #for user in users_db:
            #    data = {
            #        'chat_id': user['tid'],
            #        'text': 'Buenos días!',
            #    }
            #    r = self.send_to_bot('sendMessage', data = data)

            last_update = self.get_last_update()
            if last_update != 0:
                last_update = last_update + 1
            r = self.send_to_bot('getUpdates?timeout=30&offset={0}'.format(last_update))
            if not r:
                continue
            r_json = r.json()
            #print (r_json)
            if not r_json['ok']:
                break

            # Detect acumulated messages
            chats = {}
            for result in r_json['result']:
                chat_id = result['message']['chat']['id']
                if chat_id not in chats:
                    chats[ chat_id ] = []
                chats[ chat_id ].append(result['message'])
                if result['update_id'] >= self.get_last_update():
                    self.set_last_update (result['update_id'])

            #print (chats)
            for chat in chats:
                msgs = []
                # Too much messages to handle?
                messages_count = len(chats[chat])
                if messages_count > 3:
                    msgs.append(['{0} Me distraje un momento y ya tengo {1} notificaciones!'.format(self.emoji_oh, messages_count)])
                    # Process only first message
                    chats[chat] = [chats[chat][0]]

                for message in chats[chat]:
                #for result in r_json['result']:
                    children = None
                    infer = None
                    if_not = None
                    keys = []

                    chat_id = message['chat']['id']

                    # Text
                    if 'text' not in message:
                        continue
                    
                    text = message['text']
                    msgs_commands = []
                    if text == '/help' or text == '/help@{0}'.format(self.bot_username):
                        msgs_commands.append([self.help_text])
                        self.send_msg(msgs_commands, chat_id)
                        continue
                    elif text == '/start' or text == '/start@{0}'.format(self.bot_username):
                        msgs_commands.append([self.help_text])
                        self.send_msg(msgs_commands, chat_id)
                        continue
                    elif text == '/settings' or text == '/settings@{0}'.format(self.bot_username):
                        msgs_commands.append([self.settins_text])
                        self.send_msg(msgs_commands, chat_id)
                        continue
                    elif text == '/pause' or text == '/pause@{0}'.format(self.bot_username):
                        msgs_commands.append([self.pause_text])
                        self.pause(chat_id, True)
                        self.send_msg(msgs_commands, chat_id)
                        continue
                    elif text == '/continue' or text == '/continue@{0}'.format(self.bot_username):
                        msgs_commands.append([self.continue_text])
                        self.pause(chat_id, False)
                        self.send_msg(msgs_commands, chat_id)
                        continue
                    elif text == '/chats' or text == '/chats@{0}'.format(self.bot_username):
                        chats_stats = self.get_chats_stats()
                        msgs_commands.append(['[Terminal Start]\nChats: {0}\nLongitud promedio: {1}\nRatio promedio: {2}\nMensajes: {3}\n[Terminal End]'.format(chats_stats['count'], chats_stats['average_lenght'], chats_stats['average_ratio'], chats_stats['msg_count'])])
                        self.send_msg(msgs_commands, chat_id)
                        continue
                    
                    if text[0] == '/' and text != '/foto':
                        continue
                    elif text[0:9] == '@{0} '.format(self.bot_username):
                        text = text[10:]

                    elif text[0:12] == 'add-picture ':
                        self.add_picture(text[12:], message['from']['id'])
                        continue
                    elif text[0:11] == 'push-story ':
                        self.push_msg(text[11:], message['from']['id'])
                        continue

                    self.add_chat_lenght(chat_id)
                    chat_lenght = self.get_chat_lenght(chat_id)
                    print ('chat lenght {0}'.format(chat_lenght))

                    picture = self.get_picture(chat_id)
                    if picture:
                        #print (picture)
                        msgs.append(['https://instagram.com/p/{0}'.format(picture[0])])
                        self.chat_picture(picture[0], chat_id)
                    
                    if 0 == chat_lenght % 10 and chat_lenght <= 100:
                        msgs.append(['Califica con 5 estrellas a {0} en StoreBot!\nhttps://telegram.me/storebot?start={0}'.format(self.bot_username)])

                    self.send_msg(msgs, chat_id)


Bot = bot()

while 1:
    Bot.bot_loop()
    try:
        Bot.bot_loop()
    except KeyboardInterrupt:
        break
    except:
        print ('Exception')
