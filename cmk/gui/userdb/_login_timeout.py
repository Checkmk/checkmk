#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
We timeout users based on the number of failed authentication attempts and when a certain number
of users are timed out from the same IP, an IP wide timeout is applied. Real or fake users
are treated equally.
"""

import json
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Final

from pydantic import BaseModel, Field

from cmk.ccc.store import RealIo
from cmk.ccc.user import UserId
from cmk.utils import paths
from cmk.utils.local_secrets import LoginTimeoutSecret

TIMEOUT_DATA_FILE: Final = paths.var_dir / "login_timeout.mk"

ENTRY_STORAGE_LIFETIME: Final = timedelta(minutes=3)

USER_ATTEMPT_LIMIT: Final = 5
USER_TIMEOUT_DURATION: Final = timedelta(minutes=1)

IP_TIMEOUT_LIMIT: Final = 2
IP_TIMEOUT_DURATION: Final = timedelta(minutes=15)


def is_locked(
    limit: int,
    attempt_count: int,
    duration: timedelta,
    timed_out_at: datetime | None,
    last_attempt: datetime,
    now: datetime,
) -> bool:
    if attempt_count < limit or timed_out_at is None:
        return False
    return now - timed_out_at < duration


class UserEntry(BaseModel):
    last_attempt: datetime
    timed_out_at: datetime | None = None
    attempts: int

    @property
    def attempt_count(self) -> int:
        return self.attempts

    @property
    def limit(self) -> int:
        return USER_ATTEMPT_LIMIT

    @property
    def duration(self) -> timedelta:
        return USER_TIMEOUT_DURATION

    def is_locked(self, now: datetime) -> bool:
        return is_locked(
            self.limit, self.attempt_count, self.duration, self.timed_out_at, self.last_attempt, now
        )

    def add_attempt(self, now: datetime) -> None:
        was_locked = self.is_locked(now)
        self.attempts += 1
        self.last_attempt = now
        if not was_locked and self.attempts >= self.limit:
            # Do not reset timeout on failed attempts in window
            self.timed_out_at = now


class IPEntry(BaseModel):
    last_attempt: datetime
    timed_out_at: datetime | None = None
    attempts: list[str]

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def limit(self) -> int:
        return IP_TIMEOUT_LIMIT

    @property
    def duration(self) -> timedelta:
        return IP_TIMEOUT_DURATION

    def is_locked(self, now: datetime) -> bool:
        return is_locked(
            self.limit, self.attempt_count, self.duration, self.timed_out_at, self.last_attempt, now
        )

    def add_attempt(self, user_id: UserId, now: datetime) -> None:
        was_locked = self.is_locked(now)
        if user_id not in self.attempts:
            self.attempts.append(user_id)
        self.last_attempt = now
        if not was_locked and len(self.attempts) >= self.limit:
            self.timed_out_at = now


class TimeoutData(BaseModel):
    users: dict[str, UserEntry] = Field(default_factory=dict)
    ips: dict[str, IPEntry] = Field(default_factory=dict)

    def cleanup(self, now: datetime) -> None:
        """Remove any entry that has exceeded its lifetime unless its tracking an active timeout"""

        def _filter_entries[T: (UserEntry, IPEntry)](entries: Mapping[str, T]) -> dict[str, T]:
            return {
                k: v
                for k, v in entries.items()
                if v.is_locked(now) or now - v.last_attempt <= ENTRY_STORAGE_LIFETIME
            }

        self.users = _filter_entries(self.users)
        self.ips = _filter_entries(self.ips)


def _hash_ip(remote_ip: str) -> str:
    return LoginTimeoutSecret().secret.hmac(remote_ip.encode()).hex()


class LoginTimeoutStore:
    def __init__(self) -> None:
        self._io: Final = RealIo(TIMEOUT_DATA_FILE)

    @contextmanager
    def _locked(self) -> Generator[None]:
        yield from self._io.locked()

    def _read(self) -> TimeoutData:
        raw = self._io.read()
        return TimeoutData.model_validate(json.loads(raw)) if raw else TimeoutData()

    def _write(self, data: TimeoutData) -> None:
        self._io.write(data.model_dump_json().encode())

    @contextmanager
    def read_write_locked(self, now: datetime) -> Generator[TimeoutData]:
        with self._locked():
            data = self._read()
            yield data
            self._write(data)

    def is_timed_out(self, user_id: UserId, remote_ip: str | None, now: datetime) -> bool:
        with self.read_write_locked(now) as data:
            data.cleanup(now)
            ip_entry = data.ips.get(_hash_ip(remote_ip)) if remote_ip else None
            if ip_entry is not None and ip_entry.is_locked(now):
                return True
            user_entry = data.users.get(user_id)
            return user_entry is not None and user_entry.is_locked(now)

    def record_failed_login(self, user_id: UserId, remote_ip: str | None, now: datetime) -> None:
        with self.read_write_locked(now) as data:
            data.cleanup(now)
            user_entry = data.users.setdefault(user_id, UserEntry(attempts=0, last_attempt=now))
            user_currently_locked = user_entry.is_locked(now)
            user_entry.add_attempt(now)

            # Each locked out user should only have a max weight of 1 account, ie the same account failing
            # another login attempt when already locked, should not count as 2 accounts locked out
            if remote_ip and not user_currently_locked and user_entry.attempts >= user_entry.limit:
                ip_hash = _hash_ip(remote_ip)
                ip_entry = data.ips.setdefault(ip_hash, IPEntry(attempts=[], last_attempt=now))
                ip_entry.add_attempt(user_id, now)

    def clear_on_success(self, user_id: UserId, now: datetime) -> None:
        with self.read_write_locked(now) as data:
            data.cleanup(now)
            if user_id in data.users:
                del data.users[user_id]
