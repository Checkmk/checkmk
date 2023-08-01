#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import hmac
import math
import secrets
from enum import Enum

from cmk.utils.crypto import HashAlgorithm


class TotpVersion(Enum):
    one = 1
    rfc_totp = 0


class TOTP:
    """
    This class handles the logic for processing Time-based One Time Pins as per
    RFC6238 and the needs of Google Authenticator at the time of development.
    """

    def __init__(
        self,
        secret: bytes,
        version: TotpVersion = TotpVersion.one,
    ) -> None:
        self.secret = secret
        self.time_step = 30
        self.allowed_drift = 1
        if version == TotpVersion.one:
            self.algorithm = HashAlgorithm.Sha1
            self.code_length = 6
        elif version == TotpVersion.rfc_totp:
            self.algorithm = HashAlgorithm.Sha1
            self.code_length = 8
        else:
            raise ValueError(f"Unknown version {version}")

    @classmethod
    def generate_secret(cls, length: int = 10) -> bytes:
        """
        Defaults to 10 which is below RFC spec but is what Google
        Authenticator accepts.
        """
        return secrets.token_bytes(length)

    def hmac_hash(self, counter: int) -> hmac.HMAC:
        """
        Generate hmac based on rfc4226 where counter is a 8 byte length value
        Currently limited to SHA1
        """
        return hmac.new(self.secret, counter.to_bytes(length=8), self.algorithm.to_hashlib)

    def generate_hotp(self, hash_object: hmac.HMAC) -> int:
        """
        Convert hash to binary as we need to get the last nibble as a 0-15 value offset.
        Then pull the 4 bytes of 1: offset ... 4 offset+3
        Then return the last x int characters where x is the code length (currently 6)

        >>> TOTP("secret",TotpVersion.one).generate_hotp(hmac.HMAC(b"key", b"msg", HashAlgorithm.Sha1.to_hashlib))
        823142

        """
        digest = hash_object.digest()
        offset = digest[-1] & 0xF

        binary = (
            ((digest[offset] & 0x7F) << 24)
            | ((digest[offset + 1] & 0xFF) << 16)
            | ((digest[offset + 2] & 0xFF) << 8)
            | (digest[offset + 3] & 0xFF)
        )
        return binary % 10**self.code_length

    def calculate_generation(self, current_time: datetime.datetime) -> int:
        return math.floor(current_time.timestamp() / self.time_step)

    def generate_totp(
        self,
        generation_time: int,
    ) -> str:
        return self.generate_totp_by_generation(generation_time)

    def generate_totp_by_generation(self, generation: int) -> str:
        hash_object = self.hmac_hash(generation)
        totp = self.generate_hotp(hash_object)
        return str(totp).zfill(self.code_length)

    def check_totp(self, totp: str, generation_time: int) -> bool:
        """
        We provide leeway of step_time (30s) * 3 by determining the TOTP for the provided
        time (T), T - step_time   seconds before and T + step_time seconds after.
        """
        for generation in range(
            generation_time - self.allowed_drift, generation_time + 1 + self.allowed_drift
        ):
            if totp == self.generate_totp_by_generation(generation):
                return True
        return False
