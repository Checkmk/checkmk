#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import tempfile
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import load_pem_x509_certificate

from tests.testlib.site import Site


@pytest.fixture(name="ca_certificate_path", scope="session")
def get_site_ca_certificate_path(site: Site) -> Iterator[str]:
    """Extracts the site's CA certificate from etc/ssl/ca.pem,
    writes it to a temporary file, and returns the file path.
    """
    ca_pem_bytes = site.read_file("etc/ssl/ca.pem").encode("utf-8")
    temp_dir = tempfile.mkdtemp()
    cert_path = os.path.join(temp_dir, "ca.pem")
    with open(cert_path, "wb") as f:
        f.write(load_pem_x509_certificate(ca_pem_bytes).public_bytes(Encoding.PEM))
    yield cert_path
    os.remove(cert_path)
