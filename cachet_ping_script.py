#!/usr/bin/env python3
import asyncio
import datetime
import json
import logging
import os
import subprocess
from json import JSONDecodeError
from pprint import pformat
from typing import List, Union

import requests
from aiohttp import web

BASE_URL = "https://status.stusta.de"

IR_IP_ADDR = os.environ.get("IR_IP_ADDR", default="2001:4ca0:200:1::1")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", default="bogus_auth_token")

FIRST_INCIDENT_AFTER_SECONDS = 60
ELEVATE_INCIDENT_AFTER_SECONDS = 5 * 60

# Logger Setup
logger = logging.getLogger()
if bool(os.environ.get("DEBUG_OUTPUT", default=False)):
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())


class Component:

    def __init__(self, component_name: str):
        self.component_number = None
        self.component_name = None
        self.last_success = None
        self.incident_number = None
        self.incident_elevated = False
        self.component_status = None

        url = f"{BASE_URL}/api/v1/components"
        headers = {
            "X-Cachet-Token": AUTH_TOKEN
        }

        response = requests.request("GET", url, headers=headers)
        component_list = json.loads(response.text)["data"]

        try:
            component_desc = next(filter(lambda x: x["name"] == component_name, component_list))
        except StopIteration as e:
            logger.error("I didn't find the component", component_name)
            logger.error(pformat(component_list))
            return

        self.component_number = component_desc["id"]
        self.component_name = component_desc["name"]
        self.component_status = component_desc["status"]

    async def start(self):
        pass

    def create_incident(
            self,
            name: str,
            message: str = "There is a problem with this service.",
            component_status: int = 2,
            incident_status: int = 1):

        url = f"{BASE_URL}/api/v1/incidents"
        payload = {
            "notify": False,
            "name": name,
            "component_id": self.component_number,
            "component_status": component_status,
            "status": incident_status,
            "message": message
        }
        headers = {
            "Content-Type": "application/json",
            "X-Cachet-Token": AUTH_TOKEN
        }

        response = requests.request("POST", url, headers=headers, json=payload)
        try:
            incident = json.loads(response.text)
        except JSONDecodeError:
            logger.warning("Cachet server did not answer with json:", response.text)
            return

        logger.info("Created Incident")
        logger.info(pformat(incident))
        try:
            self.incident_number = incident["data"]["id"]
        except KeyError:
            logger.warning("Incident is not formatted correctly. Missing [data][id]")
            return

        self.component_status = component_status

    def update_incident(
            self,
            id: Union[int, None] = None,
            component_status: Union[int, None] = None,
            incident_status: Union[int, None] = 1,
            should_notify: Union[bool, None] = False):

        if id is None:
            id = self.incident_number
        if component_status is None:
            component_status = self.component_status

        url = f"{BASE_URL}/api/v1/incidents/{id}"
        headers = {
            "Content-Type": "application/json",
            "X-Cachet-Token": AUTH_TOKEN
        }
        payload = {
            "component_status": component_status,
            "status": incident_status,
            "notify": should_notify,
            "component_id": self.component_number
        }
        response = requests.request("PUT", url, headers=headers, json=payload)
        incident_update = json.loads(response.text)
        logger.debug(pformat(incident_update))

        self.component_status = component_status

    def delete_active_incident(self):
        if self.incident_number is None:
            return
        self.update_incident(component_status=1)

        url = f"{BASE_URL}/api/v1/incidents/{self.incident_number}"
        headers = {
            "Content-Type": "application/json",
            "X-Cachet-Token": AUTH_TOKEN
        }

        response = requests.request("DELETE", url, headers=headers)

        logger.debug("Incident deleted in component", self.component_name, "with status:", response.status_code,
                     "with return:")
        logger.debug(pformat(response.text))

        self.incident_number = None
        self.incident_elevated = False

    def elevate_incident(self, should_notify: bool = False):
        self.update_incident(component_status=4, should_notify=should_notify)
        self.incident_elevated = True

    def reset_last_success(self):
        self.last_success = None

    def resolve_incident(self):
        self.update_incident(component_status=1, incident_status=4)
        self.incident_elevated = False
        self.incident_number = None

    """
        Returns True if everything alright, else False
    """

    def check_and_update_status(
            self,
            name: str, msg: str,
            first_incident_seconds: int = FIRST_INCIDENT_AFTER_SECONDS,
            elevate_incident_seconds: int = ELEVATE_INCIDENT_AFTER_SECONDS,
            should_notify: bool = False):

        curtime = datetime.datetime.now()

        # if we are even seeing that something was once online. The observation begins with the first successful test. 
        if self.last_success is None:
            return True
        tdelta = (curtime - self.last_success).total_seconds()
        logger.debug(f"Checking current status of {self.component_name}; Secs since last confirm: {tdelta}; "
                     f"Secs till first notify: {first_incident_seconds - tdelta}")

        # we have a lasting problem
        if (self.incident_number is not None) and not self.incident_elevated and (tdelta > elevate_incident_seconds):
            logger.info(f"{self.component_name}: Incident elevated")
            self.elevate_incident(should_notify=should_notify)
            return False

        # we experience the first problem
        if (self.incident_number is None) and (tdelta > first_incident_seconds):
            logger.info(f"{self.component_name}: Incident raised")
            self.create_incident(name=name, message=msg)
            self.incident_elevated = False
            return False

        # we are okay again
        if (self.incident_number is not None) and tdelta < first_incident_seconds:
            logger.info(f"{self.component_name}: Incident resolved")
            self.resolve_incident()
            return True

        return True


class IR(Component):

    def __init__(self):
        super().__init__("Internal Router")

    async def start(self):
        asyncio.create_task(self.ping_loop())

    async def ping_loop(self):
        while True:
            process = subprocess.run(["ping", "-6", "-c", "1", IR_IP_ADDR], capture_output=True)
            logger.debug("Ping")
            if process.returncode == 0:
                self.last_success = datetime.datetime.now()

            await asyncio.sleep(25)

    def check_and_update_status(self):
        logger.debug("in IR check function")

        return super().check_and_update_status(
            "IR downtime detected",
            "Our automatic failure detection has found that the Internal Router of the Studentenwerk is down. "
            "This is most likely due to a reboot. It should come online again shortly. "
            "These reboots, unfortunately, are not under our control."
        )


class NAT(Component):

    def __init__(self):
        super().__init__("NAT")

    async def start(self):
        await asyncio.start_server(self.tcp_callback, "0.0.0.0", 7331)

    async def tcp_callback(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        logger.debug("got TCP request...")

        try:
            timestamp_str = await reader.readline()
            timestamp_sent = datetime.datetime.fromtimestamp(int(timestamp_str.decode("utf8")))
        except:  # ignore malformed requests
            return

        tdelta = datetime.datetime.now() - timestamp_sent
        if abs(tdelta.total_seconds()) < 30:
            logger.debug("TCP request is from NAT")
            self.last_success = datetime.datetime.now()
            writer.write(b"OK")
        else:
            writer.write(b"FAIL")

    def check_and_update_status(self):
        logger.debug("in NAT check function")

        return super().check_and_update_status(
            "NAT downtime detected",
            "Our automatic failure detection has found that the NAT loop is experiencing issues. "
            "That means, you don't have internet in your rooms right now. "
            "We will try to resolve them as fast as possible, sorry for the inconvenience.",
            should_notify=True
        )


class Proxy(Component):

    def __init__(self):
        super().__init__("Proxy")

    async def start(self):
        http_server = web.Application()
        http_server.add_routes([web.get("/http-ping", self.http_callback)])
        asyncio.create_task(web._run_app(http_server, port=7332))

    async def http_callback(self, request: web.Request):
        logger.debug("got an http request...")

        headers = request.headers
        timestamp_str = headers.get("Timestamp")

        if timestamp_str is None:
            return web.Response(text="Header Fail")

        try:
            timestamp_sent = datetime.datetime.fromtimestamp(int(timestamp_str))
        except:
            return web.Response(text="ERROR: not a valid timestamp in header")

        tdelta = datetime.datetime.now() - timestamp_sent
        if abs(tdelta.total_seconds()) < 30:
            logger.debug("http request is from Proxy!")

            self.last_success = datetime.datetime.now()
            return web.Response(text="OK")
        else:
            return web.Response(text="FAIL")

    def check_and_update_status(self):
        logger.debug("in Proxy check funtion")
        return super().check_and_update_status(
            "Proxy downtime detected",
            "Our automatic failure detection has found that the Proxy is experiencing issues. "
            "That means, if you are using the Proxy, you are experiencing issues with your internet connection. "
            "We will try to resolve them as fast as possible, sorry for the inconvenience.",
            should_notify=True
        )


async def test_loop(blocking_service: Component, nonblocking_services: List[Component]):
    await blocking_service.start()
    for service in nonblocking_services:
        await service.start()

    logger.debug("Finished setting up the objects")

    while True:
        if blocking_service.check_and_update_status():
            for service in nonblocking_services:
                service.check_and_update_status()

        else:
            for service in nonblocking_services:
                service.delete_active_incident()  # we can safely assume that the incident was caused by the blocking_service failing
                service.reset_last_success()

        logger.debug("Testloop executed")

        await asyncio.sleep(5)


def main():
    ir = IR()
    nat = NAT()
    proxy = Proxy()
    asyncio.run(test_loop(ir, [nat, proxy]))


if __name__ == "__main__":
    main()
