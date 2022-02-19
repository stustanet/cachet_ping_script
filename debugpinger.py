#!/usr/bin/env python3
import asyncio
import datetime

import requests


async def loop_function():
    while (True):
        timestamp = str(int(datetime.datetime.now().timestamp())) + "\n"
        print(timestamp)
        header = {"Timestamp": timestamp.strip()}

        req = requests.request("GET", "http://127.0.0.1:7332/http-ping", headers=header)
        print("Answer from http endpoint", req.text)

        reader, writer = await asyncio.open_connection("127.0.0.1", 7331)
        writer.write(timestamp.encode("utf8"))
        await writer.drain()
        answer = await reader.readline()
        print("Answer from TCP endpoint", answer)
        await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(loop_function())
