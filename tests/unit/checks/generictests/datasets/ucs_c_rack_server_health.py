checkname = 'ucs_c_rack_server_health'

info = [[
    'storageControllerHealth', 'dn sys/rack-unit-1/board/storage-SAS-SLOT-HBA/vd-0', 'health Good'
],
        [
            'storageControllerHealth', 'dn sys/rack-unit-2/board/storage-SAS-SLOT-HBA/vd-0',
            'health AnythingElse'
        ]]

discovery = {
    '': [('Rack unit 1 Storage SAS SLOT HBA vd 0', {}), ('Rack unit 2 Storage SAS SLOT HBA vd 0',
                                                         {})]
}

checks = {
    '': [('Rack unit 1 Storage SAS SLOT HBA vd 0', {}, [(0, 'Status: good', [])]),
         ('Rack unit 2 Storage SAS SLOT HBA vd 0', {}, [(3, 'Status: unknown[anythingelse]', [])])]
}
