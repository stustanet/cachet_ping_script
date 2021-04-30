#!/usr/bin/python3

import socket
import datetime
import time
import os

def request_loop():
    while True:
        time_str = str(int(datetime.datetime.now().timestamp())) + "\n"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((os.environ.get("CACHET_PING_LINK", "cachet.stusta.de"), 7331))
                sock.send(time_str.encode("utf8"))
                print("done")
                recieve_str = sock.recv(4)
                print("recv")
                if recieve_str != b"OK":
                    print(time_str+":", "Failed to get valid response:", recieve_str)
                sock.close()
        except:
            print("Error during tcp ping execution")

        time.sleep(25)


request_loop()
