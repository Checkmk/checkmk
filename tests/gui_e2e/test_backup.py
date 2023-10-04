#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re

from playwright.sync_api import expect

from tests.testlib.playwright.helpers import PPage

_backup_passphrase = "cmk"


def _go_to_backups_page(logged_in_page: PPage) -> None:
    logged_in_page.megamenu_setup.click()
    logged_in_page.main_menu.get_text("Backups").click()


def _create_backup_target(logged_in_page: PPage) -> None:
    logged_in_page.main_area.get_suggestion("Backup targets").click()
    logged_in_page.main_area.expect_no_entries()

    logged_in_page.main_area.get_suggestion("Add target").click()
    logged_in_page.main_area.get_input("edit_target_p_ident").fill("mytarget")
    logged_in_page.main_area.get_input("edit_target_p_title").fill("My backup target")
    logged_in_page.main_area.get_input("edit_target_p_remote_0_p_path").fill("/tmp")
    logged_in_page.main_area.get_text("Is mountpoint").uncheck()

    logged_in_page.main_area.get_suggestion("Save").click()


def _create_encryption_key(logged_in_page: PPage) -> None:
    logged_in_page.main_area.get_suggestion("Backup encryption keys").click()
    logged_in_page.main_area.expect_no_entries()

    logged_in_page.main_area.get_suggestion("Add key").click()
    logged_in_page.main_area.get_input("key_p_alias").fill("My backup key")
    logged_in_page.main_area.get_input("key_p_passphrase").fill(_backup_passphrase)
    logged_in_page.main_area.get_suggestion("Create").click()
    logged_in_page.main_area.check_warning(
        re.compile(".*The following keys have not been downloaded yet: My backup key.*")
    )


def _create_backup_job(logged_in_page: PPage) -> None:
    logged_in_page.main_area.get_suggestion("Add job").click()
    logged_in_page.main_area.get_input("edit_job_p_ident").fill("mybackup")
    logged_in_page.main_area.get_input("edit_job_p_title").fill("My backup")
    logged_in_page.main_area.get_text("Compress the backed up files").check()

    logged_in_page.main_area.locator_via_xpath("span", "Do not encrypt the backup").click()
    logged_in_page.main_area.locator_via_xpath("li", "Encrypt the backup using the key:").click()
    logged_in_page.click_and_wait(
        locator=logged_in_page.main_area.locator_via_xpath("span", "My backup key"),
        reload_on_error=True,
    )
    logged_in_page.main_area.get_suggestion("Save").click()


def _start_backup(logged_in_page: PPage) -> None:
    # todo: reload needed to refresh the status bar (see CMK-11721). Once the issue is fixed,
    #  remove reload.
    logged_in_page.click_and_wait(
        locator=logged_in_page.main_area.get_link_from_title("Manually start this backup"),
        expected_locator=logged_in_page.main_area.locator_via_xpath("span", "Finished"),
        reload_on_error=True,
    )


def _restore_backup(logged_in_page: PPage) -> None:
    logged_in_page.main_area.get_suggestion("Restore").click()
    logged_in_page.main_area.get_link_from_title("Restore from this backup target").click()
    logged_in_page.main_area.get_link_from_title("Start restore of this backup").click()
    expect(logged_in_page.main_area.get_text("Start restore of backup")).to_be_visible()
    logged_in_page.main_area.locator_via_xpath("button", "Start").click()

    logged_in_page.main_area.get_input("_key_p_passphrase").fill(_backup_passphrase)

    # From the documentation:
    # 'After restoring, the site will be restarted, so you will temporarily see an HTTP 503 error
    # message'
    # This is the reason why we need to wait for the restoring to be completed while trying to
    # reload the page.
    logged_in_page.click_and_wait(
        locator=logged_in_page.main_area.get_text("Start restore"),
        expected_locator=logged_in_page.main_area.get_text("Restore completed"),
        reload_on_error=True,
    )

    logged_in_page.main_area.get_suggestion("Complete the restore").click()


def _cleanup(logged_in_page: PPage) -> None:
    """Remove the created backup job, target and encryption key."""
    _go_to_backups_page(logged_in_page)

    # remove job
    logged_in_page.main_area.get_link_from_title("Delete this backup job").click()
    logged_in_page.main_area.locator_via_xpath("button", "Delete").click()
    logged_in_page.main_area.expect_no_entries()

    # remove target
    _go_to_backups_page(logged_in_page)
    logged_in_page.main_area.get_suggestion("Backup targets").click()
    logged_in_page.main_area.get_link_from_title("Delete this backup target").click()
    logged_in_page.main_area.locator_via_xpath("button", "Delete").click()
    logged_in_page.main_area.expect_no_entries()

    # remove encryption key
    _go_to_backups_page(logged_in_page)
    logged_in_page.main_area.get_suggestion("Backup encryption keys").click()
    logged_in_page.main_area.get_link_from_title("Delete this key").click()
    logged_in_page.main_area.locator_via_xpath("button", "Delete").click()
    logged_in_page.main_area.expect_no_entries()


def test_backups(logged_in_page: PPage) -> None:
    _go_to_backups_page(logged_in_page)
    logged_in_page.main_area.expect_no_entries()

    _create_backup_target(logged_in_page)
    _go_to_backups_page(logged_in_page)

    _create_encryption_key(logged_in_page)
    _go_to_backups_page(logged_in_page)

    _create_backup_job(logged_in_page)
    _start_backup(logged_in_page)
    _restore_backup(logged_in_page)

    _cleanup(logged_in_page)
