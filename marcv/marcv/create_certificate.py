#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import random
import sys
from pathlib import Path
from typing import Tuple

from OpenSSL import crypto
from OpenSSL.SSL import FILETYPE_PEM

from marcv.constants import CERT_NOT_AFTER, ROOT_CERT, SERVER_CERT, SERVER_CN, SERVER_PRIVATE_KEY
from marcv.log import logger


def certificate_exists(cert_path: Path, key_path: Path) -> bool:
    return cert_path.exists() and key_path.exists()


def make_private_key() -> crypto.PKey:
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    return key


def read_pem(path: Path) -> Tuple[crypto.X509, crypto.PKey]:
    with path.open(mode="rb") as f:
        file_contents = f.read()
        cert = crypto.load_certificate(FILETYPE_PEM, file_contents)
        key = crypto.load_privatekey(FILETYPE_PEM, file_contents)
    return cert, key


def get_certificate(
    name: str,
    root_cert: crypto.X509,
    root_key: crypto.PKey,
    private_key: crypto.PKey,
    cert_not_after: int,
):
    req = crypto.X509Req()
    req.get_subject().CN = name
    req.set_pubkey(private_key)
    req.sign(private_key, "sha512")

    cert = crypto.X509()
    cert.set_serial_number(random.randint(0, sys.maxsize))
    cert.set_version(2)
    cert.get_subject().CN = name

    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(cert_not_after)
    cert.set_issuer(root_cert.get_subject())
    cert.set_pubkey(req.get_pubkey())
    cert.add_extensions(
        [crypto.X509Extension(b"subjectAltName", False, f"DNS:{name}".encode("utf-8"))]
    )

    cert.sign(root_key, "sha512")

    return cert


def create_certificate(
    name: str, root_pem: Path, cert_path: Path, key_path: Path, cert_not_after: int
):
    root_cert, root_key = read_pem(root_pem)
    private_key = make_private_key()
    cert = get_certificate(name, root_cert, root_key, private_key, cert_not_after)

    cert_path.write_bytes(crypto.dump_certificate(FILETYPE_PEM, cert))
    key_path.write_bytes(crypto.dump_privatekey(FILETYPE_PEM, private_key))

    logger.info(f"Server certificate {cert_path} successfully created.")


def main():
    if certificate_exists(SERVER_CERT, SERVER_PRIVATE_KEY):
        logger.info(f"Server certificate already created")
        return

    create_certificate(
        SERVER_CN, ROOT_CERT, SERVER_CERT, SERVER_PRIVATE_KEY, CERT_NOT_AFTER
    )

    if not certificate_exists(SERVER_CERT, SERVER_PRIVATE_KEY):
        logger.error(f"Server certificate creation failed")
        sys.exit(1)
