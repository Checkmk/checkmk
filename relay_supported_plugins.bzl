"""List of plugin families and active checks supported by the relay component."""

# After changing this, run 'make relock_venv'
# to update the Python dependencies of the relay
RELAY_SUPPORTED_PLUGIN_FAMILIES = [
    "cisco_prime",
    "ipmi",
    "kube",
    "lib",
    "netapp",
    "prism",
    "proxmox_ve",
    "pure_storage_fa",
    "rabbitmq",
    "randomds",
    "redfish",
    "splunk",
    "vsphere",
]

# Single source of truth for the relay-supported active checks:
# check name -> the Bazel target that provides its binary.
# The keys drive the cmk.active_check_supported_on_relay entry-point group
# (cmk/BUILD, read by the site-side dispatch gate); the values are the
# active-check binaries bundled into the relay image (omd/non-free/relay/BUILD).
# cmk_inv is deliberately absent: HW/SW Inventory runs on the SITE and uses the
# relay only as a fetcher, so it must never be dispatched to a relay.
RELAY_SUPPORTED_ACTIVE_CHECKS = {
    "cert": "//omd/packages/check-cert:check-cert",
    "httpv2": "//packages/check-http:check_http_tar",
    "icmp": "//omd/packages/monitoring-plugins:check_icmp",
}
