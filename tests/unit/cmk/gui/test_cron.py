import cmk.gui.cron as cron


def test_registered_jobs():
    found_jobs = sorted(["%s.%s" % (f.__module__, f.__name__) for f in cron.multisite_cronjobs])
    assert found_jobs == sorted([
        'cmk.gui.cee.reporting.cleanup_stored_reports',
        'cmk.gui.cee.reporting.do_scheduled_reports',
        'cmk.gui.inventory.run',
        'cmk.gui.plugins.cron.gui_background_job.housekeeping',
        'cmk.gui.plugins.cron.wato_folder_lookup_cache.rebuild_folder_lookup_cache',
        'cmk.gui.userdb.execute_userdb_job',
        'cmk.gui.wato.execute_network_scan_job',
    ])
