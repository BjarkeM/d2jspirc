import websocket
import logging
import random
import math
import os
from time import sleep

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] (%(module)s.%(funcName)s): %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


class JspIRC(object):
    def __init__(self, user_id, auth_token, url="wss://chat.d2jsp.org:2053/irc"):
        self.url = url
        self.user_id = user_id
        self.auth_token = auth_token
        self.retry_count = 0
        self.max_retry_count = 15  # around 15 minutes with exponential backoff.

    def exponential_backoff(self):
        max_wait_seconds = 60
        return min(math.pow(2, self.retry_count) + random.random(), max_wait_seconds)

    def on_message(self, *args):
        if len(args) == 1:
            if args[0].startswith(':chat.d2jsp.org 652'):  # fg received message
                line = args[0][1:].split(':', 1)
                fg_message = line[1].replace('\n', ' ').strip()
                info = line[0][:-1].rsplit(' ', 3)
                user = info[1]
                user_id = info[2]
                fg_amount = info[-1]
                print(f'Received {fg_amount} from {user}{" with message: " + fg_message if fg_message else ""}')
            else:
                print(args[0])

    def on_error(self, *args):
        self.on_close()

    def on_close(self, *args):
        self.retry_count += 1
        if self.retry_count > self.max_retry_count:
            logging.error(f"No response within {self.max_retry_count} attempts! Exiting.")
            return

        sleep_time = self.exponential_backoff()
        logging.info(f"--WEBSOCKET CLOSED / ATTEMPTING RESTART IN {sleep_time} SECONDS--")
        sleep(sleep_time)
        self.start_client()

    def open_for_user(self, user_id, auth_token):
        def on_open(ws):
            self.retry_count = 0
            logging.info(f'Opened connection to {ws.url}')
            ws.send(f"NICK #{user_id}\n")
            ws.send(f"USER U{user_id} njIRCIM chat.d2jsp.org :njIRCIM User ID {user_id}\n")
            ws.send(f"FAUTH {auth_token}\n")

        return on_open

    def start_client(self):
        ws = websocket.WebSocketApp(self.url,
                                    on_message=self.on_message,
                                    on_error=self.on_error,
                                    on_close=self.on_close,
                                    on_data=self.on_message)
        ws.on_open = self.open_for_user(self.user_id, self.auth_token)
        ws.run_forever()


if __name__ == '__main__':
    user_id = os.environ.get('user_id', 'USER_ID')
    auth_token = os.environ.get('auth_token', 'AUTH_TOKEN')
    client = JspIRC(user_id, auth_token)
    client.start_client()
