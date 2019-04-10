# yapf: disable


checkname = 'mysql_ping'


info = [['this', 'line', 'is', 'ignored'],
        ['[[elephant]]'],
        ['mysqladmin:', 'connect', 'to', 'server', 'at', "'localhost'", 'failed'],
        ['[[moth]]'],
        ['mysqld', 'is', 'alive']]


discovery = {
    '': [
        ('elephant', {}),
        ('moth', {}),
    ],
}


checks = {
    '': [
        ('elephant', {}, [(2, "mysqladmin: connect to server at 'localhost' failed", [])]),
        ('moth', {}, [(0, 'MySQL Deamon is alive', [])]),
    ],
}
