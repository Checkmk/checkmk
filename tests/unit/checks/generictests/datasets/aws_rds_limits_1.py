# -*- encoding: utf-8
# yapf: disable

checkname = 'aws_rds_limits'

info = [['[["db_instances",', '"TITLE",', '10,', '1]]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'manual_snapshots': (None, 80.0, 90.0),
                'db_clusters': (None, 80.0, 90.0),
                'db_parameter_groups': (None, 80.0, 90.0),
                'option_groups': (None, 80.0, 90.0),
                'db_cluster_roles': (None, 80.0, 90.0),
                'db_security_groups': (None, 80.0, 90.0),
                'reserved_db_instances': (None, 80.0, 90.0),
                'read_replica_per_master': (None, 80.0, 90.0),
                'event_subscriptions': (None, 80.0, 90.0),
                'subnet_per_db_subnet_groups': (None, 80.0, 90.0),
                'db_cluster_parameter_groups': (None, 80.0, 90.0),
                'allocated_storage': (None, 80.0, 90.0),
                'db_subnet_groups': (None, 80.0, 90.0),
                'db_instances': (None, 80.0, 90.0),
                'auths_per_db_security_groups': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (u'aws_rds_db_instances', 1, None, None, None, None)
                    ]
                ), (0, u'\nTITLE: 1 (of max. 10)', [])
            ]
        )
    ]
}
