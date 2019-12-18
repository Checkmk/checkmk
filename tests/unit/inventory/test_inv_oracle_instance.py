import pytest


@pytest.mark.parametrize('line, inventory_data, status_data', [
    ([], {}, {}),
    ([
        'SID',
        'VERSION',
    ], {}, {}),
    (['SID', 'VERSION', 'OPENMODE', 'LOGINS', '_UNUSED1', '_UNUSED2'], {
        "sid": "SID",
        "version": "VERSION",
        "openmode": "OPENMODE",
        "logmode": None,
        "logins": "LOGINS",
        "db_creation_time": None,
    }, {
        "sid": "SID",
        "db_uptime": None,
    }),
    ([
        'SID',
        'VERSION',
        'OPENMODE',
        'LOGINS',
        '_ARCHIVER',
        'RAW_UP_SECONDS',
        '_DBID',
        'LOGMODE',
        '_DATABASE_ROLE',
        '_FORCE_LOGGING',
        '_NAME',
    ], {
        "sid": "SID",
        "version": "VERSION",
        "openmode": "OPENMODE",
        "logmode": "LOGMODE",
        "logins": "LOGINS",
        "db_creation_time": None,
    }, {
        "sid": "SID",
        "db_uptime": None,
    }),
    ([
        'SID',
        'VERSION',
        'OPENMODE',
        'LOGINS',
        '_ARCHIVER',
        '123',
        '_DBID',
        'LOGMODE',
        '_DATABASE_ROLE',
        '_FORCE_LOGGING',
        '_NAME',
    ], {
        "sid": "SID",
        "version": "VERSION",
        "openmode": "OPENMODE",
        "logmode": "LOGMODE",
        "logins": "LOGINS",
        "db_creation_time": None,
    }, {
        "sid": "SID",
        "db_uptime": 123,
    }),
    ([
        'SID',
        'VERSION',
        'OPENMODE',
        'LOGINS',
        '_ARCHIVER',
        'RAW_UP_SECONDS',
        '_DBID',
        'LOGMODE',
        '_DATABASE_ROLE',
        '_FORCE_LOGGING',
        '_NAME',
        '080220151025',
    ], {
        "sid": "SID",
        "version": "VERSION",
        "openmode": "OPENMODE",
        "logmode": 'LOGMODE',
        "logins": "LOGINS",
        "db_creation_time": "2015-02-08 10:25",
    }, {
        "sid": "SID",
        "db_uptime": None,
    }),
    ([
        'SID',
        'VERSION',
        'OPENMODE',
        'LOGINS',
        '_ARCHIVER',
        '123',
        '_DBID',
        'LOGMODE',
        '_DATABASE_ROLE',
        '_FORCE_LOGGING',
        '_NAME',
        '080220151025',
    ], {
        "sid": "SID",
        "version": "VERSION",
        "openmode": "OPENMODE",
        "logmode": 'LOGMODE',
        "logins": "LOGINS",
        "db_creation_time": "2015-02-08 10:25",
    }, {
        "sid": "SID",
        "db_uptime": 123,
    }),
    ([
        'SID',
        'VERSION',
        'OPENMODE',
        'LOGINS',
        '_ARCHIVER',
        'RAW_UP_SECONDS',
        '_DBID',
        'LOGMODE',
        '_DATABASE_ROLE',
        '_FORCE_LOGGING',
        '_NAME',
        'RAW_DB_CREATION_TIME',
        '_PLUGGABLE',
        '_CON_ID',
        '_PNAME',
        '_PDBID',
        '_POPENMODE',
        '_PRESTRICTED',
        '_PTOTAL_SIZE',
        '_PRECOVERY_STATUS',
        '_PUP_SECONDS',
        '_PBLOCK_SIZE',
    ], {
        "sid": "SID",
        "version": "VERSION",
        "openmode": "OPENMODE",
        "logmode": 'LOGMODE',
        "logins": "LOGINS",
        "db_creation_time": None,
    }, {
        "sid": "SID",
        "db_uptime": None,
    }),
    ([
        'SID',
        'VERSION',
        'OPENMODE',
        'LOGINS',
        '_ARCHIVER',
        '123',
        '_DBID',
        'LOGMODE',
        '_DATABASE_ROLE',
        '_FORCE_LOGGING',
        '_NAME',
        '080220151025',
        '_PLUGGABLE',
        '_CON_ID',
        '_PNAME',
        '_PDBID',
        '_POPENMODE',
        '_PRESTRICTED',
        '_PTOTAL_SIZE',
        '_PRECOVERY_STATUS',
        '_PUP_SECONDS',
        '_PBLOCK_SIZE',
    ], {
        "sid": "SID",
        "version": "VERSION",
        "openmode": "OPENMODE",
        "logmode": 'LOGMODE',
        "logins": "LOGINS",
        "db_creation_time": "2015-02-08 10:25",
    }, {
        "sid": "SID",
        "db_uptime": 123,
    }),
])
def test_inv_oracle_instance(inventory_plugin_manager, line, inventory_data, status_data):
    inv_plugin = inventory_plugin_manager.get_inventory_plugin('oracle_instance')
    inventory_tree_data, status_tree_data = inv_plugin.run_inventory([line])

    path = "software.applications.oracle.instance:"
    assert path in inventory_tree_data
    assert path in status_tree_data

    node_inventory_data = inventory_tree_data[path]
    if inventory_data:
        assert sorted(node_inventory_data[0].items()) == sorted(inventory_data.items())
    else:
        assert node_inventory_data == []

    node_status_data = status_tree_data[path]
    if status_data:
        assert sorted(node_status_data[0].items()) == sorted(status_data.items())
    else:
        assert node_status_data == []
