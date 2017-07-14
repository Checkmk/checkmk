#!/usr/bin/env python

import os
import time
import pytest
from testlib import web

@pytest.fixture(scope="module")
def default_cfg(web):
    print "Applying default config"
    web.add_host("livestatus-test-host", attributes={
        "ipaddress": "127.0.0.1",
    })

    web.discover_services("livestatus-test-host")

    web.activate_changes()
    yield None

    #
    # Cleanup code
    #
    print "Cleaning up default config"

    web.delete_host("livestatus-test-host")


def _toggle_liveproxyd(site, use_liveproxyd):
    cfg = "on" if use_liveproxyd else "off"
    site.set_config("LIVEPROXYD", cfg, with_restart=True)

    if use_liveproxyd:
        assert site.file_exists("tmp/run/liveproxyd.pid")
    else:
        assert not site.file_exists("tmp/run/liveproxyd.pid")


def _change_liveproxyd_sites(site, sites):
    site.write_file("etc/check_mk/liveproxyd.mk",
        """sites.update(%r)""" % sites)

    # Cleanup all existing socket files
    site.execute(["rm", "tmp/run/liveproxy/*"])

    # Trigger config reload
    os.kill(int(site.read_file("tmp/run/liveproxyd.pid").strip()), 10) # SIGHUP

    def _all_sockets_opened():
        return all([ site.file_exists("tmp/run/liveproxy/%s" % site_id)
                     for site_id in sites.keys() ])

    timeout = time.time() + 60
    while timeout > time.time() and not _all_sockets_opened():
        time.sleep(0.5)

    assert _all_sockets_opened(), "Liveproxyd sockets not opened after 60 seconds"


def _use_liveproxyd_for_local_site(site, proto="unix"):
    if proto != None:
        if proto == "unix":
            socket = None
        else:
            socket = ("127.0.0.1", site.livestatus_port)

        sites = {
            site.id: {
                'cache': True,
                'channel_timeout': 3.0,
                'channels': 5,
                'connect_retry': 4.0,
                'heartbeat': (5, 2.0),
                'query_timeout': 120.0,
                'socket': socket,
            }
        }
    else:
        sites = {}

    _change_liveproxyd_sites(site, sites)


@pytest.mark.parametrize(("use_liveproxyd"), [ True, False ])
def test_omd_toggle(default_cfg, site, use_liveproxyd):
    _toggle_liveproxyd(site, use_liveproxyd)


@pytest.mark.parametrize(("proto"), [ "unix", "tcp" ])
def test_simple_query(default_cfg, site, proto):
    import livestatus

    if proto == "tcp":
        site.open_livestatus_tcp()

    _toggle_liveproxyd(site, use_liveproxyd=True)
    _use_liveproxyd_for_local_site(site, proto=proto)

    live = livestatus.MultiSiteConnection(
        sites={
            site.id: {
                'alias': u'Der Master',
                'customer': 'provider',
                'disable_wato': True,
                'disabled': False,
                'insecure': False,
                'multisiteurl': '', 
                'persist': False,
                'replicate_ec': False,
                'replicate_mkps': False,
                'replication': '', 
                'socket': "unix:%s/tmp/run/liveproxy/%s" % (site.root, site.id),
                'status_host': None,
                'timeout': 10, 
                'user_login': True,
                'user_sync': 'all',
            }
        }
    )

    assert live.dead_sites() == {}

    rows = live.query("GET hosts")
    assert type(rows) == list
    assert len(rows) >= 2 # header + min 1 host


def test_large_number_of_sites(default_cfg, site):
    import livestatus

    _toggle_liveproxyd(site, use_liveproxyd=True)

    # Increase nofiles limit of CMC to prevent that it runs in "too many open files" resource limits
    exit_code = site.execute(["prlimit", "-p", site.read_file("tmp/run/cmc.pid").strip(), "-n4096"]).wait()
    assert exit_code == 0

    site_sockets, num_sites, num_channels = {}, 600, 3
    for site_num in range(num_sites):
        # Currently connect to local site
        site_id = "site%03d" % site_num

        site_sockets[site_id] = {
            "to_livestatus" : None,
            "to_proxy"      : "unix:%s/tmp/run/liveproxy/%s" % (site.root, site_id),
        }

    liveproxyd_sites, livestatus_api_sites = {}, {}

    for site_id, site_sockets in site_sockets.items():
        liveproxyd_sites[site_id] = {
            'cache': False,
            'channel_timeout': 3.0,
            'channels': num_channels,
            'connect_retry': 4.0,
            'heartbeat': (5, 2.0),
            'query_timeout': 120.0,
            'socket': site_sockets["to_livestatus"],
        }

        livestatus_api_sites[site_id] ={
            'alias': u'Site %s' % site_id,
            'disable_wato': True,
            'disabled': False,
            'insecure': False,
            'multisiteurl': '', 
            'persist': False,
            'replicate_ec': False,
            'replicate_mkps': False,
            'replication': '', 
            'socket': site_sockets["to_proxy"],
            'status_host': None,
            'timeout': 2, 
            'user_login': True,
            'user_sync': 'all',
        }

    try:
        site.write_file("etc/check_mk/conf.d/liveproxyd-test.mk",
            "cmc_livestatus_threads = %d\n" % (num_channels*num_sites + 20))

        site.execute(["cmk", "-O"])

        # Disable limits of livestatus xinetd service
        #site.execute(["sed", "-i", "-r",
        #                "'/^\s+cps\s+=/d;/^\s+instances\s+=/d;/^\s+per_source\s+=/d'",
        #                "etc/xinetd.d/mk-livestatus"])
        #site.execute(["omd", "restart", "xinetd"])

        _change_liveproxyd_sites(site, liveproxyd_sites)

        def _num_connections_opened():
            # Need to reconstruct the object on each call because connect is
            # currently done in constructor :-/
            live = livestatus.MultiSiteConnection(livestatus_api_sites)
            assert live.dead_sites() == {}

            live.set_prepend_site(True)
            rows = live.query("GET status\nColumns: program_version\n")
            live.set_prepend_site(False)

            assert type(rows) == list
            return len(rows)

        # Wait up to 30 seconds for all connections to be established. When opening so
        # many connections to one cmc at the time some connects may fail temporarily
        timeout = time.time() + 90
        while timeout > time.time() and _num_connections_opened() != len(livestatus_api_sites):
            time.sleep(0.5)

        num_open = _num_connections_opened()
        assert num_open == len(livestatus_api_sites), \
            "Liveproxyd sockets not opened after 60 seconds"

    finally:
        _use_liveproxyd_for_local_site(site, proto="unix")
        site.delete_file("etc/check_mk/conf.d/liveproxyd-test.mk")
