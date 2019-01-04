

checkname = 'prism_alerts'


info = [['timestamp', 'message', 'severity'],
        ['1456749413140000',
         'DIMM fault detected on host 172.25.209.110. The node is running with 384 GB whereas 512 GB was installed.',
         'kCritical'],
        ['1456749413150000', 'Some warning message.', 'kWarning'],
        ['1456749413160000', 'Some info message.', 'kInfo']]


discovery = {'': [(None, None)]}


checks = {'': [(None,
                {},
                [(0,
                  '3 alerts, Last worst on Mon Feb 29 13:36:53 2016: "Some info message."',
                  [])])]}