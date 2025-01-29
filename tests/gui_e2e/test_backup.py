#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from playwright.sync_api import expect

from tests.testlib.playwright.pom.dashboard import Dashboard

_backup_passphrase = "cmk-12-chars"


def _go_to_backups_page(dashboard_page: Dashboard) -> None:
    dashboard_page.main_menu.setup_menu("Backups").click()


def _create_backup_target(dashboard_page: Dashboard) -> None:
    dashboard_page.main_area.get_suggestion("Backup targets").click()
    dashboard_page.main_area.expect_no_entries()

    dashboard_page.main_area.get_suggestion("Add target").click()
    dashboard_page.main_area.get_input("edit_target_p_ident").fill("mytarget")
    dashboard_page.main_area.get_input("edit_target_p_title").fill("My backup target")
    dashboard_page.main_area.get_input("edit_target_p_remote_0_p_path").fill("/tmp")
    dashboard_page.main_area.get_text("Is mountpoint").uncheck()

    dashboard_page.main_area.get_suggestion("Save").click()


def _create_encryption_key(dashboard_page: Dashboard) -> None:
    dashboard_page.main_area.get_suggestion("Backup encryption keys").click()
    dashboard_page.main_area.expect_no_entries()

    # Use a too short password
    dashboard_page.main_area.get_suggestion("Generate key").click()
    dashboard_page.main_area.get_input("key_p_alias").fill("Won't work")
    dashboard_page.main_area.get_input("key_p_passphrase").fill("tooshort")
    dashboard_page.main_area.get_suggestion("Create").click()
    dashboard_page.main_area.check_error("You need to provide at least 12 characters.")

    dashboard_page.main_area.get_input("key_p_alias").fill("My backup key")
    dashboard_page.main_area.get_input("key_p_passphrase").fill(_backup_passphrase)
    dashboard_page.main_area.get_suggestion("Create").click()
    dashboard_page.main_area.check_warning(
        re.compile(".*The following keys have not been downloaded yet: My backup key.*")
    )


def _create_backup_job(dashboard_page: Dashboard) -> None:
    dashboard_page.main_area.get_suggestion("Add job").click()
    dashboard_page.main_area.get_input("edit_job_p_ident").fill("mybackup")
    dashboard_page.main_area.get_input("edit_job_p_title").fill("My backup")
    dashboard_page.main_area.get_text("Compress the backed up files").check()

    dashboard_page.main_area.locator_via_xpath("span", "Do not encrypt the backup").click()
    dashboard_page.main_area.locator_via_xpath("span", "Encrypt the backup using the key:").click()
    dashboard_page.click_and_wait(
        locator=dashboard_page.main_area.locator_via_xpath("span", "My backup key"),
        reload_on_error=True,
    )
    dashboard_page.main_area.get_suggestion("Save").click()


def _start_backup(dashboard_page: Dashboard) -> None:
    # todo: reload needed to refresh the status bar (see CMK-11721). Once the issue is fixed,
    #  remove reload.
    dashboard_page.click_and_wait(
        locator=dashboard_page.main_area.get_link_from_title("Manually start this backup"),
        expected_locator=dashboard_page.main_area.locator_via_xpath("span", "Finished"),
        reload_on_error=True,
    )


def _restore_backup(dashboard_page: Dashboard) -> None:
    dashboard_page.main_area.get_suggestion("Restore").click()
    dashboard_page.main_area.get_link_from_title("Restore from this backup target").click()
    dashboard_page.main_area.get_link_from_title("Start restore of this backup").click()
    expect(
        dashboard_page.main_area.get_text("Start restore of backup", exact=False)
    ).to_be_visible()
    dashboard_page.main_area.locator_via_xpath("button", "Start").click()

    dashboard_page.main_area.get_input("_key_p_passphrase").fill(_backup_passphrase)

    # From the documentation:
    # 'After restoring, the site will be restarted, so you will temporarily see an HTTP 503 error
    # message'
    # This is the reason why we need to wait for the restoring to be completed while trying to
    # reload the page.
    dashboard_page.click_and_wait(
        locator=dashboard_page.main_area.get_text("Start restore", exact=False),
        expected_locator=dashboard_page.main_area.get_text("Restore completed", exact=False),
        reload_on_error=True,
    )

    dashboard_page.main_area.get_suggestion("Complete the restore").click()


def _cleanup(dashboard_page: Dashboard) -> None:
    """Remove the created backup job, target and encryption key."""
    _go_to_backups_page(dashboard_page)

    # remove job
    dashboard_page.main_area.get_link_from_title("Delete this backup job").click()
    dashboard_page.main_area.locator_via_xpath("button", "Delete").click()
    dashboard_page.main_area.expect_no_entries()

    # remove target
    _go_to_backups_page(dashboard_page)
    dashboard_page.main_area.get_suggestion("Backup targets").click()
    dashboard_page.main_area.get_link_from_title("Delete this backup target").click()
    dashboard_page.main_area.locator_via_xpath("button", "Delete").click()
    dashboard_page.main_area.expect_no_entries()

    # remove encryption key
    _go_to_backups_page(dashboard_page)
    dashboard_page.main_area.get_suggestion("Backup encryption keys").click()
    dashboard_page.main_area.get_link_from_title("Delete this key").click()
    dashboard_page.main_area.locator_via_xpath("button", "Delete").click()
    dashboard_page.main_area.expect_no_entries()


def test_backups(dashboard_page: Dashboard) -> None:
    _go_to_backups_page(dashboard_page)
    dashboard_page.main_area.expect_no_entries()

    _create_backup_target(dashboard_page)
    _go_to_backups_page(dashboard_page)

    _create_encryption_key(dashboard_page)
    _go_to_backups_page(dashboard_page)

    _create_backup_job(dashboard_page)
    _start_backup(dashboard_page)
    _restore_backup(dashboard_page)

    _cleanup(dashboard_page)
