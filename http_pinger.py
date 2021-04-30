#!/usr/bin/python3
import requests
import datetime
import os
import time

def request_loop():
    while True:
        time_str = str(int(datetime.datetime.now().timestamp()))
        header = {"Timestamp": time_str}
        try:
            req = requests.request("GET", os.environ.get("CACHET_PING_LINK", default="http://cachet.stusta.de:7332/http-ping"), headers=header)
            if req.status_code != 200 or req.text.find("OK") == -1:
                print(time_str+":", "got invalid response: Code", req.status_code, "Text:", req.text)
        except:
            print("Error during http ping execution")
        time.sleep(25)  

request_loop()
