"""
settings
    chat_id             - Unique user identifier
    key                 - Specific setting key (string)
    value               - Value for the setting key (string)
    - model
    - prompt
    - temperature
    - max_tokens
    - max_history_tokens
current_chats
    chat_id             - Unique user identifier
    chat_history        - Whole conversation history, in a single JSON
saved_chats
    chat_id             - Unique user identifier
    chat_name           - Name under which the chat history is saved (string)
    chat_history        - Whole conversation history, saved under chat_name
"""

import sqlite3
import json

##########
## INIT ##
##########


def init_db():
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                (chat_id INTEGER, key TEXT, value TEXT, PRIMARY KEY (chat_id, key))''')
    c.execute('''CREATE TABLE IF NOT EXISTS current_chats
                (chat_id INTEGER PRIMARY KEY, chat_history TEXT DEFAULT '[]')''')
    c.execute('''CREATE TABLE IF NOT EXISTS saved_chats
                (chat_id INTEGER, chat_name TEXT, chat_history TEXT, PRIMARY KEY (chat_id, chat_name))''')
    conn.commit()
    conn.close()


def init_user(chat_id):
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO current_chats(chat_id) VALUES(?)", (chat_id,))
    conn.commit()
    conn.close()


##############
## SETTINGS ##
##############


def key_get(chat_id, key):
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE chat_id=? AND key=?", (chat_id, key))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


def key_set(chat_id, key, value):
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings(chat_id, key, value) VALUES(?, ?, ?)", (chat_id, key, value))
    conn.commit()
    conn.close()


def key_remove(chat_id, key):
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute("DELETE FROM settings WHERE chat_id=? AND key=?", (chat_id, key))
    conn.commit()
    conn.close()


#############
## HISTORY ##
#############


def history_get(chat_id):
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute("SELECT chat_history FROM current_chats WHERE chat_id=?", (chat_id,))
    history_str = c.fetchone()[0]
    history = json.loads(history_str)
    conn.close()
    return history


def history_update(chat_id, chat_history):
    chat_history_str = json.dumps(chat_history, ensure_ascii=False)
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute("UPDATE current_chats SET chat_history=? WHERE chat_id=?", (chat_history_str, chat_id))
    conn.commit()
    conn.close()


#####################
## CHAT_MANAGEMENT ##
#####################


def chat_save(chat_id, chat_name):
    current_history = history_get(chat_id)
    chat_history_str = json.dumps(current_history, ensure_ascii=False)
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO saved_chats(chat_id, chat_name, chat_history) VALUES(?, ?, ?)",
              (chat_id, chat_name, chat_history_str))
    conn.commit()
    conn.close()
    chat_forget(chat_id)


def chat_load(chat_id, chat_name):
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute("SELECT chat_name, chat_history FROM saved_chats WHERE chat_id=? AND chat_name LIKE ?", (chat_id, f"%{chat_name}%"))
    results = c.fetchall()
    
    if len(results) == 0:
        response_message = f"❔ No chats found for \"{chat_name}\""
    elif len(results) > 1:
        matching_chats = "\n".join(result[0] for result in results)
        response_message = f"❔ Multiple chats found for \"{chat_name}\":\n{matching_chats}\n\nPick specific one!"
    else:
        result = results[0]
        history_str = result[1]
        history = json.loads(history_str)
        history_update(chat_id, history)
        c.execute("DELETE FROM saved_chats WHERE chat_id=? AND chat_name=?", (chat_id, result[0]))
        conn.commit()
        response_message = f"✨ Chat '{result[0]}' loaded!"

    conn.close()
    return response_message


def chat_forget(chat_id, chat_name=""):
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    
    if chat_name == "":
        # Current chat
        c.execute("UPDATE current_chats SET chat_history='[]' WHERE chat_id=?", (chat_id,))
        response_message = "✨ History cleared!"
    elif chat_name.lower() == "all":
        # All chats
        c.execute("DELETE FROM saved_chats WHERE chat_id=?", (chat_id,))
        c.execute("UPDATE current_chats SET chat_history='[]' WHERE chat_id=?", (chat_id,))
        response_message = "✨ History cleared for all chats!"
    else:
        # Specific chat 
        c.execute("SELECT chat_name FROM saved_chats WHERE chat_id=? AND chat_name LIKE ?", (chat_id, f"%{chat_name}%"))
        matches = c.fetchall()
        if len(matches) == 0:
            response_message = f"❔ No chats found for \"{chat_name}\""
        elif len(matches) > 1:
            matching_chats = "\n".join(match[0] for match in matches)
            response_message = f"❔ Multiple chats found for \"{chat_name}\":\n{matching_chats}\n\nPick specific one!"
        else:
            c.execute("DELETE FROM saved_chats WHERE chat_id=? AND chat_name=?", (chat_id, matches[0][0]))
            response_message = f"✨ Chat '{matches[0][0]}' deleted!"
    
    conn.commit()
    conn.close()
    return response_message


def chat_list(chat_id):
    conn = sqlite3.connect('y_userdata.db')
    c = conn.cursor()
    c.execute("SELECT chat_name FROM saved_chats WHERE chat_id=?", (chat_id,))
    chats = c.fetchall()
    conn.close()
    return [chat[0] for chat in chats]
