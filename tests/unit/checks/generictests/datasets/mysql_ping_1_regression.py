# yapf: disable


checkname = 'mysql_ping'


info = [
    ['this', 'line', 'is', 'no', 'longer', 'ignored'],
    ['[[elephant]]'],
    ['mysqladmin:', 'connect', 'to', 'server', 'at', "'localhost'", 'failed'],
    ['[[moth]]'],
    ['mysqld', 'is', 'alive'],
]


discovery = {
    '': [
        ('mysql', {}),
        ('elephant', {}),
        ('moth', {}),
    ],
}


checks = {
    '': [
        ('mysql', {}, [(2, 'this line is no longer ignored', [])]),
        ('elephant', {}, [(2, "mysqladmin: connect to server at 'localhost' failed", [])]),
        ('moth', {}, [(0, 'MySQL Deamon is alive', [])]),
    ],
}
