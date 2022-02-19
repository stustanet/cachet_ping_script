# Cachet Ping Script

Script to check the internet connection from the StuSta to our external server.
If a connection fails, e.g. if the router is rebooting, an automatic incident is created on [our status site](status.stusta.de).
The status site runs with [Cachet](https://cachethq.io/). The script uses its api to manage the incidents.

## Architecture
`cachet_ping_script.py` runs on the external server and handles the incidents.
The `*pinger.py` run in the stusta on Hugin and connect to the external server.
If the connection fails, one or more servers are not working correctly.

## Handled Servers
If a service was unavailable for 60 seconds an incident is created.
In Case the router is offline, the other components are ignored, as the router is needed to connect to them.

### Internal Router (IR)
The script sends icmp echo requests to the router and checks if echo replies are received. This is possible as the router has a public IP.

### Natter
To check if Natter is offline a tcp connection is created regularly with `tcp_pinger.py`.

### Proxy
The HTTP Proxy is checked with `http_pinger.py`. The Proxy server is used automatically from the system configuration.