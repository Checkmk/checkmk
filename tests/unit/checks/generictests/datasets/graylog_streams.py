# -*- encoding: utf-8
# yapf: disable
checkname = 'graylog_streams'

info = [
    [
        u'{"total": 5, "streams": [{"remove_matches_from_default_stream": false, "is_default": false, "index_set_id": "5da58758e2847e0602771f2a", "description": "logins", "alert_conditions": [], "rules": [], "outputs": [], "created_at": "2019-10-21T11:32:54.371Z", "title": "Logins", "disabled": false, "content_pack": null, "matching_type": "AND", "creator_user_id": "admin", "alert_receivers": {"emails": [], "users": []}, "id": "5dad97665bc77407a731e7dc"}, {"remove_matches_from_default_stream": false, "is_default": false, "index_set_id": "5d64cceecaba8d12890fdf47", "description": "dfh", "alert_conditions": [], "rules": [], "outputs": [], "created_at": "2019-10-30T19:45:31.792Z", "title": "shsdfhg", "disabled": false, "content_pack": null, "matching_type": "AND", "creator_user_id": "admin", "alert_receivers": {"emails": [], "users": []}, "id": "5db9e85b9a74aa6ccbb8e1b0"}, {"remove_matches_from_default_stream": false, "is_default": true, "index_set_id": "5d64cceecaba8d12890fdf47", "description": "Stream containing all messages", "alert_conditions": [], "rules": [], "outputs": [], "created_at": "2019-08-27T06:25:50.570Z", "title": "All messages", "disabled": false, "content_pack": null, "matching_type": "AND", "creator_user_id": "local:admin", "alert_receivers": {"emails": [], "users": []}, "id": "000000000000000000000001"}, {"remove_matches_from_default_stream": true, "is_default": false, "index_set_id": "5da58758e2847e0602771f28", "description": "Stream containing all events created by Graylog", "alert_conditions": [], "rules": [{"description": "", "stream_id": "000000000000000000000002", "value": ".*", "inverted": false, "field": ".*", "type": 2, "id": "5dad59d65bc77407a731a2fc"}], "outputs": [], "created_at": "2019-10-15T08:46:16.321Z", "title": "All events", "disabled": false, "content_pack": null, "matching_type": "AND", "creator_user_id": "admin", "alert_receivers": {"emails": [], "users": []}, "id": "000000000000000000000002"}, {"remove_matches_from_default_stream": true, "is_default": false, "index_set_id": "5da58758e2847e0602771f2a", "description": "Stream containing all system events created by Graylog", "alert_conditions": [], "rules": [], "outputs": [], "created_at": "2019-10-15T08:46:16.327Z", "title": "All system events", "disabled": false, "content_pack": null, "matching_type": "AND", "creator_user_id": "admin", "alert_receivers": {"emails": [], "users": []}, "id": "000000000000000000000003"}]}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'stream_disabled': 1
            }, [
                (
                    0, 'Number of streams: 5', [
                        ('num_streams', 5, None, None, None, None)
                    ]
                ), (0, u'Default stream: All messages', []),
                (0, 'see long output for more details', []),
                (0, u'\nAll events', []), (0, u'\nAll messages (default)', []),
                (0, u'\nAll system events', []), (0, u'\nLogins', []),
                (0, u'\nshsdfhg', [])
            ]
        )
    ]
}
