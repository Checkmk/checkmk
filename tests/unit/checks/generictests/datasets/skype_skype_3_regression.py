#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'skype'

info = [
    [u'sampletime', u'14425512178844', u'10000000'],
    [u'[LS:A/V Edge - UDP Counters]'],
    [u'instance', u'A/V Edge - Total Relay Sessions',
     u'A/V Edge - Active Relay Sessions - Authenticated',
     u'A/V Edge - Active Relay Sessions - Allocated Port',
     u'A/V Edge - Active Relay Sessions - Data',
     u'A/V Edge - Allocated Port Pool Count',
     u'A/V Edge - Allocated Port Pool Miss Count',
     u'A/V Edge - Allocate Requests/sec',
     u'A/V Edge - Authentication Failures',
     u'A/V Edge - Authentication Failures/sec',
     u'A/V Edge - Allocate Requests Exceeding Port Limit',
     u'A/V Edge - Allocate Requests Exceeding Port Limit/sec',
     u'A/V Edge - Alternate Server Redirects',
     u'A/V Edge - Alternate Server Redirects/sec',
     u'A/V Edge - Client Request Errors (4xx Responses)',
     u'A/V Edge - Client Request Errors/sec (4xx Responses/sec)',
     u'A/V Edge - Client SetActiveDestination Request Errors',
     u'A/V Edge - Client SetActiveDestination Request Errors/sec',
     u'A/V Edge - Session Idle Timeouts/sec',
     u'A/V Edge - Packets Received/sec',
     u'A/V Edge - Packets Sent/sec',
     u'A/V Edge - Average TURN Packet Latency (milliseconds)',
     u' ',
     u'A/V Edge - Average Data Packet Latency (milliseconds)',
     u' ',
     u'A/V Edge - Average TURN BW Packet Latency (milliseconds)',
     u' ',
     u'A/V Edge - Maximum Packet Latency (milliseconds)',
     u'A/V Edge - Packets Dropped/sec',
     u'A/V Edge - Packets Not Forwarded/sec',
     u'A/V Edge - Average Depth of Connection Receive Queue',
     u' ',
     u'A/V Edge - Maximum Depth of Connection Receive Queue',
     u'A/V Edge - Active Sessions Exceeding Avg Bandwidth Limit',
     u'A/V Edge - Active Sessions Exceeding Peak Bandwidth Limit',
     u'A/V Edge - Active Federated UDP Sessions',
     u'A/V Edge - Active Federated UDP Sessions/sec'],
    [u'_Total', u'127527', u'1', u'1', u'1', u'373', u'0', u'380527', u'74', u'74', u'0', u'0',
     u'0', u'0', u'131633', u'131633', u'0', u'0', u'36901', u'81751143', u'81195598', u'0',
     u'0', u'83137339', u'81518637', u'0', u'0', u'632', u'0', u'117987', u'106330854',
     u'81547681', u'183', u'0', u'0', u'0', u'0'],
    [u'Private IPv4 Network Interface', u'121187', u'1', u'1', u'1', u'0', u'0', u'361037',
     u'31', u'31', u'0', u'0', u'0', u'0', u'124524', u'124524', u'0', u'0', u'5893',
     u'47237024', u'31686484', u'0', u'0', u'47742041', u'47236960', u'0', u'0', u'23', u'0',
     u'2957', u'67615154', u'47236959', u'81', u'0', u'0', u'0', u'0'],
    [u'Public IPv4 Network Interface', u'6340', u'0', u'0', u'0', u'373', u'0', u'19490', u'43',
     u'43', u'0', u'0', u'0', u'0', u'7109', u'7109', u'0', u'0', u'31008', u'34514119',
     u'49509114', u'0', u'0', u'35395298', u'34281677', u'0', u'0', u'609', u'0', u'115030',
     u'38715700', u'34310722', u'102', u'0', u'0', u'0', u'0'],
    [u'Private IPv6 Network Interface', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
     u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
     u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'],
    [u'Public IPv6 Network Interface', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
     u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
     u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0']]


checks = {
 'edge': [(None, {'authentication_failures': {'upper': (20, 40)},
                  'allocate_requests_exceeding': {"upper": (20, 40)},
                  'packets_dropped': {"upper": (200, 400)},
                  },
           [(0, 'UDP auth failures/sec: 0.00', [('edge_udp_failed_auth', 0.0, 20, 40, None, None)]),
            # The check crashed here with a KeyError.
            (0, '', []),
            # end
            (0, 'UDP allocate requests > port limit/sec: 0.00', [
               ('edge_udp_allocate_requests_exceeding_port_limit', 0.0, 20, 40, None, None)]),
            (0, '', []),
            (0, 'UDP packets dropped/sec: 0.00', [
             ('edge_udp_packets_dropped', 0.0, 200, 400, None, None)]),
            (0, '', [])]
           )],
}
