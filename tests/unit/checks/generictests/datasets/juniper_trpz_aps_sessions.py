# yapf: disable


checkname = 'juniper_trpz_aps_sessions'


info = [[[None, '12.109.103.48.50.49.52.49.56.49.54.52.57', '10', 'AP-RTSG01-R29']],
        [[None,
          '12.109.103.48.50.49.52.49.56.49.54.52.57.1',
          '0',
          '0',
          '0',
          '0',
          '0',
          '0',
          '0',
          '0',
          '0',
          '0',
          '0']],
        [[None, '12.109.103.48.50.49.52.49.56.48.55.57.50', '7', 'AP-D16-Schwille']],
        [[None,
          '12.109.103.48.50.49.52.49.56.48.55.57.50.2',
          '878622',
          '722521169',
          '259010759',
          '80213977575',
          '53258427',
          '3911398497',
          '84355',
          '78',
          '160792',
          '0',
          '-116']]]


discovery = {'': [('D16-Schwille', None)]}


checks = {'': [('D16-Schwille',
                {},
                [(0, 'Status: operational', []),
                 (0,
                  'Radio 2: Input: 0.00 B/s, Output: 0.00 B/s, Errors: 0, Resets: 0, Retries: 0, Sessions: 0, Noise: -116 dBm',
                  [('if_out_unicast', 0, None, None, None, None),
                   ('if_out_unicast_octets', 0.0, None, None, None, None),
                   ('if_out_non_unicast', 0.0, None, None, None, None),
                   ('if_out_non_unicast_octets', 0.0, None, None, None, None),
                   ('if_in_pkts', 0.0, None, None, None, None),
                   ('if_in_octets', 0.0, None, None, None, None),
                   ('wlan_physical_errors', 0.0, None, None, None, None),
                   ('wlan_resets', 0.0, None, None, None, None),
                   ('wlan_retries', 0.0, None, None, None, None),
                   ('total_sessions', 0, None, None, None, None),
                   ('noise_floor', -116, None, None, None, None)])])]}