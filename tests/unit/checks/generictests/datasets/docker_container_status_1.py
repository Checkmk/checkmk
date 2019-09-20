# -*- encoding: utf-8
# yapf: disable


checkname = 'docker_container_status'


info = [[u'@docker_version_info',
         u'{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.39"}'],
        [u'{"Status": "running", "Healthcheck": {"Test": ["CMD-SHELL", "/healthcheck.sh"]}, "Pid": 0, "OOMKilled": false, "Dead": false, "RestartPolicy": {"MaximumRetryCount": 0, "Name": "no"}, "Paused": false, "Running": false, "FinishedAt": "2019-06-05T13:52:46.75115293Z", "Health": {"Status": "unhealthy", "Log": [{"Start": "2019-06-05T15:50:23.329542773+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:50:23.703382311+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:50:53.724749309+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:50:54.082847699+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:51:24.10105535+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:51:24.479921663+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:51:54.531087549+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:51:54.891176872+02:00", "ExitCode": 0}, {"Start": "2019-06-05T15:52:24.911587947+02:00", "Output": "mysqld is alive\\n", "End": "2019-06-05T15:52:25.256847222+02:00", "ExitCode": 0}], "FailingStreak": 0}, "Restarting": false, "Error": "", "StartedAt": "2019-06-05T08:58:06.893459004Z", "ExitCode": 0}']]


freeze_time = "2019-06-05T09:40:06.893459004Z"


discovery = {
    '': [(None, {})],
    'health': [(None, {})],
    'uptime': [(None, {})],
}


extra_sections = {
    '': [[]],
    'health': [[]],
    'uptime': [[]],
}

checks = {
    '': [
        (None, {}, [
            (0, u'Container running', []),
        ]),
    ],
    'health': [
        (None, {}, [
            (2, u'Health status: Unhealthy', []),
            (0, u'Last health report: mysqld is alive', []),
            (2, 'Failing streak: 0', []),
            (0, "Health test: u'CMD-SHELL /healthcheck.sh'")
        ]),
    ],
    'uptime': [
        (None, {}, [
            (0, u'Up since Wed Jun  5 10:58:06 2019 (0d 00:42:00)', [('uptime', 2520.0)]),
        ]),
    ],
}
