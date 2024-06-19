#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Management of the site local CA and certificates issued by it"""

from pathlib import Path
from typing import Final

from cmk.utils.certs import RootCA


class CertificateAuthority:
    """Management of the site local CA and certificates issued by it"""

    def __init__(
        self,
        root_ca: RootCA,
        ca_path: Path,
    ) -> None:
        super().__init__()
        self.root_ca: Final = root_ca
        self._ca_path = ca_path

    def _site_certificate_path(self, site_id: str) -> Path:
        return (self._ca_path / "sites" / site_id).with_suffix(".pem")

    def site_certificate_exists(self, site_id: str) -> bool:
        return self._site_certificate_path(site_id).exists()

    def create_site_certificate(self, site_id: str, key_size: int = 4096) -> None:
        """Creates the key / certificate for the given Check_MK site"""
        self.root_ca.issue_and_store_certificate(
            path=self._site_certificate_path(site_id),
            common_name=site_id,
            key_size=key_size,
        )
