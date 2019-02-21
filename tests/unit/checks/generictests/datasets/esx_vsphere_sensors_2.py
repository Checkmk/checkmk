# yapf: disable
checkname = 'esx_vsphere_sensors'

info = [['Dummy sensor', '', '', '', '', '', 'green', 'all is good', 'the sun is shining']]

discovery = {'': [(None, [])]}

checks = {
    '': [(None, {}, [(0, ('All sensors are in normal state\n'
                          'Sensors operating normal are:\n'
                          'Dummy sensor: all is good (the sun is shining)'), [])])]
}
