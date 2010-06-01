for _z in range(0, 100):
    _name = "zombie%04d" % _z
    all_hosts.append(_name + "|zombie")
    ipaddresses[_name] = "127.0.0.1"

datasource_programs = [
 ( "cat /var/lib/check_mk/cache/localhost", [ "zombie" ], ALL_HOSTS),
]
