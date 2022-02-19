#!/usr/bin/env python3
import datetime
import os
import time

import requests


def request_loop():
    while True:
        time_str = str(int(datetime.datetime.now().timestamp()))
        header = {"Timestamp": time_str}
        try:
            req = requests.request(
                "GET", os.environ.get("CACHET_PING_LINK", default="http://status.stusta.de:7332/http-ping"),
                headers=header)
            if req.status_code != 200 or req.text.find("OK") == -1:
                print(time_str + ":", "got invalid response: Code", req.status_code, "Text:", req.text)
        except:
            print("Error during http ping execution")
        time.sleep(25)


if __name__ == "__main__":
    request_loop()
