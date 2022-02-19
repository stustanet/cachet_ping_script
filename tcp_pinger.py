#!/usr/bin/env python3

import datetime
import os
import socket
import time


def request_loop():
    while True:
        time_str = str(int(datetime.datetime.now().timestamp())) + "\n"
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((os.environ.get("CACHET_PING_LINK", "status.stusta.de"), 7331))
                sock.send(time_str.encode("utf8"))
                print("done")
                receive_str = sock.recv(4)
                print("recv")
                if receive_str != b"OK":
                    print(time_str + ":", "Failed to get valid response:", receive_str)
                sock.close()
        except:
            print("Error during tcp ping execution")

        time.sleep(25)


if __name__ == "__main__":
    request_loop()
