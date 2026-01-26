#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module sets up environment for sending and testing email notifications.

It includes functions to configure and remove local Postfix server, wait for incoming emails,
and verify the content of received emails.
"""

import email
import logging
import time
from collections.abc import Iterator
from email.message import Message
from email.policy import default
from getpass import getuser
from pathlib import Path
from types import TracebackType
from typing import Final, IO, Self

from faker import Faker  # type: ignore[import-not-found,unused-ignore]

from tests.testlib.common.repo import repo_path
from tests.testlib.site import Site
from tests.testlib.utils import run

logger = logging.getLogger(__name__)


def message_from_file(f: IO[str]) -> Message:
    return email.message_from_file(f, policy=default)


class EmailManager:
    def __init__(self) -> None:
        self.temp_folder = Path("/tmp")
        self.base_folder: Final[Path] = Path.home()  # enforced by postfix
        self.maildir_folder = self.base_folder / "Maildir"
        self.unread_folder = self.maildir_folder / "new"
        scripts_folder = repo_path() / "tests" / "scripts"
        self.setup_postfix_script = scripts_folder / "setup_postfix.sh"
        self.teardown_postfix_script = scripts_folder / "teardown_postfix.sh"
        self._username = getuser()

    def __enter__(self) -> Self:
        self.setup_postfix()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.teardown_postfix()
        self.delete_html_file()

    @property
    def html_file_path(self) -> Path:
        return self.temp_folder / "email_content.html"

    def setup_postfix(self) -> None:
        """Install and configure Postfix to send emails to a local Maildir."""
        logger.info("Setting up postfix...")

        run([str(self.setup_postfix_script), self._username], sudo=True)
        logger.info("Postfix is set up. Unread email folder: %s", self.unread_folder)

    def teardown_postfix(self) -> None:
        """Uninstall Postfix and delete all related files."""
        logger.info("Deleting postfix and related files...")
        run([str(self.teardown_postfix_script), self._username], sudo=True)
        logger.info("Postfix is deleted")

    def find_email_by_subject(self, email_subject: str | None = None) -> Path | None:
        """Check all emails in the Maildir folder and return the file path of the email
        with the specified subject. Delete checked emails.
        """
        for file_name in self.unread_folder.iterdir():
            file_path = self.unread_folder / file_name
            with open(file_path) as file:
                msg = message_from_file(file)
                logger.info("Email received, subject: '%s'", msg.get("Subject"))
                if email_subject is None or msg.get("Subject") == email_subject:
                    return file_path
                file_path.unlink()
        return None

    def wait_for_email(
        self, email_subject: str | None = None, interval: int = 3, timeout: int = 120
    ) -> Path:
        """Wait for an email with the specified subject to be received in the Maildir folder.
        Return the file path of the email if it is received, otherwise raise TimeoutError.
        """
        subject_note = f'with subject "{email_subject}"' if email_subject else "(any subject)"
        logger.info("Waiting for email %s", subject_note)
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.unread_folder.exists():
                file_path = self.find_email_by_subject(email_subject)
                if file_path:
                    return file_path
            time.sleep(interval)
        raise TimeoutError(
            f"No email {subject_note} was received within {timeout} seconds!"
            f" (Mail folder: {self.unread_folder})"
        )

    def check_email_content(
        self,
        file_path: Path,
        expected_fields: dict[str, str],
        expected_text_content: dict[str, str],
    ) -> None:
        """Check that the email has expected fields and text content."""
        with open(file_path) as file:
            msg = message_from_file(file)
            logger.info("Check that email fields have expected values")
            for field, expected_value in expected_fields.items():
                assert msg.get(field) == expected_value, f"Field '{field}' has unexpected value"

            logger.info("Check that email text content has expected value")
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        text = payload.decode()
                    else:
                        raise ValueError("Unexpected payload type: %s" % type(payload))
                    text_dict = self.convert_text_into_dict(text)
                    for key, expected_value in expected_text_content.items():
                        actual_value = text_dict[key]
                        assert expected_value == actual_value, f"Field '{key}' has unexpected value"

    def copy_html_content_into_file(self, file_path: Path) -> Path:
        """Copy the html content of the email into a file and return the file path."""
        with open(file_path) as file:
            msg = message_from_file(file)
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        html_content = payload.decode()
                    else:
                        raise ValueError("Unexpected payload type")
                    with open(self.html_file_path, "w") as html_file:
                        html_file.write(html_content)
                    break
        return self.html_file_path.absolute()

    def delete_html_file(self) -> None:
        """Delete the html file if exists."""
        if self.html_file_path.exists():
            logger.info("Delete the html file with email content")
            self.html_file_path.unlink()

    @staticmethod
    def convert_text_into_dict(text: str) -> dict[str, str]:
        """Convert text content of the email into a dictionary."""
        lines = text.split("\n")
        dict_result = {}
        for line in lines:
            if ": " in line:
                key, value = line.split(": ", 1)
                dict_result[key.strip()] = value.strip()
        return dict_result

    def clean_emails(self, email_subject: str | None = None) -> None:
        if not self.unread_folder.exists():
            logger.info(
                "Skipping emails cleaning because unread folder ('%s') does not exist",
                self.unread_folder,
            )
            return

        while file_path := self.find_email_by_subject(email_subject):
            file_path.unlink()


def create_notification_user(site: Site, admin: bool = False) -> Iterator[tuple[str, str]]:
    """Create a user for email notifications via API.

    Create a user with email in order to receive email notifications.
    Delete the user after the test.
    """
    faker = Faker()
    user_name = faker.user_name()
    email_address = f"{user_name}@test.com"

    site.openapi.users.create(
        username=user_name,
        fullname=faker.name(),
        password=faker.password(length=12),
        email=email_address,
        contactgroups=["all"],
        roles=["admin"] if admin else [],
    )
    site.openapi.changes.activate_and_wait_for_completion()
    yield user_name, email_address
    site.openapi.users.delete(user_name)
    site.openapi.changes.activate_and_wait_for_completion()
