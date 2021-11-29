#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import Optional

from agent_receiver.constants import AGENT_OUTPUT_DIR
from cryptography.x509 import load_pem_x509_csr
from cryptography.x509.oid import NameOID


def uuid_from_pem_csr(pem_csr: str) -> str:
    try:
        return (
            load_pem_x509_csr(pem_csr.encode())
            .subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
            .value
        )
    except ValueError:
        return "[CSR parsing failed]"


def get_hostname_from_link(uuid: str) -> Optional[str]:
    link_path = AGENT_OUTPUT_DIR / uuid

    try:
        target_path = os.readlink(link_path)
    except FileNotFoundError:
        return None

    return Path(target_path).name
