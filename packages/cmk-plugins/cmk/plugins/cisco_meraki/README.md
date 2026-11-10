# Cisco Meraki

Monitoring for **Cisco Meraki** cloud-managed network devices (appliances,
switches, wireless access points and sensors).

Data is collected by the `agent_cisco_meraki` special agent, which queries the
Meraki Dashboard API for an organisation's licenses, networks, devices and
their statuses, uplinks, VPNs, switch ports, wireless and sensor readings. The
check plugins in this package parse that data to monitor device health,
licensing, uplink and VPN status, appliance performance and environmental
sensors, and contribute HW/SW inventory.
