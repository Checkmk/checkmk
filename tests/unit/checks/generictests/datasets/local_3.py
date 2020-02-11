# -*- encoding: utf-8
# yapf: disable
checkname = 'local'

info = [
    [
        None,
        u'0 "my service" count1=42|count2=21;23;27|count3=73 OK - This is my custom output'
    ],
    [
        None,
        u'0 myservice1 count1=42|count2=21;23;27|count3=73 OK This is my custom output'
    ],
    [
        None,
        u'0 "my super service1" count1=42|count2=21;23;27|count3=73 OK: This is my custom output'
    ], [None, u'0 "my super service" - OK - This is my custom output'],
    [None, u'0 "my-super-service" - OK - This is my custom output']
]

discovery = {
    '': [
        ('my service', {}),
        ('my super service', {}), ('my super service1', {}),
        ('my-super-service', {}), ('myservice1', {})
    ]
}

checks = {
    '': [
        (
            'my service', {}, [
                (
                    0, 'OK - This is my custom output', [
                        ('count1', 42.0, None, None, None, None),
                        ('count2', 21.0, 23.0, 27.0, None, None),
                        ('count3', 73.0, None, None, None, None)
                    ]
                )
            ]
        ),
        ('my super service', {}, [(0, 'OK - This is my custom output', [])]),
        (
            'my super service1', {}, [
                (
                    0, 'OK: This is my custom output', [
                        ('count1', 42.0, None, None, None, None),
                        ('count2', 21.0, 23.0, 27.0, None, None),
                        ('count3', 73.0, None, None, None, None)
                    ]
                )
            ]
        ),
        ('my-super-service', {}, [(0, 'OK - This is my custom output', [])]),
        (
            'myservice1', {}, [
                (
                    0, 'OK This is my custom output', [
                        ('count1', 42.0, None, None, None, None),
                        ('count2', 21.0, 23.0, 27.0, None, None),
                        ('count3', 73.0, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
