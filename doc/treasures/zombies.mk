# Put this file into etc/check_mk/conf.d and you
# will get a number of virtual host monitoring
# the same data as 'localhost'. You might
# have to adapt the path to the cache file
# see below
#
# Why should that be usefull? Performance testing.
# GUI testing...

_num_zombies = 100


for _z in range(0, _num_zombies):
    _name = "zombie%04d" % _z
    all_hosts.append(_name + "|zombie")
    ipaddresses[_name] = "127.0.0.1"

datasource_programs = [
 ( "cat /var/lib/check_mk/cache/localhost", [ "zombie" ], ALL_HOSTS),
]
