#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
#       U  ___ u  __  __   ____
#        \/"_ \/U|' \/ '|u|  _"\
#        | | | |\| |\/| |/| | | |
#    .-,_| |_| | | |  | |U| |_| |\
#     \_)-\___/  |_|  |_| |____/ u
#          \\   <<,-,,-.   |||_
#         (__)   (./  \.) (__)_)
#
# This file is part of OMD - The Open Monitoring Distribution.
# The official homepage is at <http://omdistro.org>.
#
# OMD  is  free software;  you  can  redistribute it  and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the  Free Software  Foundation  in  version 2.  OMD  is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Management of the site local CA and certificates issued by it"""

from pathlib import Path
from typing import Iterable, Tuple

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKeyWithSerialization
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat
from cryptography.x509 import Certificate

from cmk.utils.certs import (
    load_cert_and_private_key,
    make_csr,
    make_private_key,
    make_root_certificate,
    make_subject_name,
    root_cert_path,
    sign_csr,
)

CERT_NOT_AFTER = 999 * 365  # 999 years by default
CA_CERT_NOT_AFTER = CERT_NOT_AFTER


class CertificateAuthority:
    """Management of the site local CA and certificates issued by it"""

    def __init__(self, ca_path: Path, ca_name: str) -> None:
        super().__init__()
        self._ca_path = ca_path
        self._ca_name = ca_name
        self._marcv_cert_path = ca_path / "marcv_cert.pem"

    @property
    def _root_cert_path(self) -> Path:
        return root_cert_path(self._ca_path)

    def _site_certificate_path(self, site_id: str) -> Path:
        return (self._ca_path / "sites" / site_id).with_suffix(".pem")

    def _create_root_certificate(self) -> Tuple[Certificate, RSAPrivateKeyWithSerialization]:
        return (
            make_root_certificate(
                make_subject_name(self._ca_name),
                CA_CERT_NOT_AFTER,
                private_key := make_private_key(),
            ),
            private_key,
        )

    def _get_root_certificate(self) -> Tuple[Certificate, RSAPrivateKeyWithSerialization]:
        return load_cert_and_private_key(self._root_cert_path)

    def _certificate_from_root(self, cn: str) -> Tuple[Certificate, RSAPrivateKeyWithSerialization]:
        if not self.is_initialized:
            raise RuntimeError("Certificate authority is not initialized yet")
        private_key = make_private_key()
        return (
            sign_csr(
                make_csr(
                    make_subject_name(cn),
                    private_key,
                ),
                CERT_NOT_AFTER,
                *self._get_root_certificate(),
            ),
            private_key,
        )

    @staticmethod
    def _serialize_certificate(certificate: Certificate) -> bytes:
        return certificate.public_bytes(Encoding.PEM)

    @staticmethod
    def _serialize_private_key(private_key: RSAPrivateKeyWithSerialization) -> bytes:
        return private_key.private_bytes(
            Encoding.PEM,
            PrivateFormat.PKCS8,
            NoEncryption(),
        )

    def _write_cert_chain(
        self,
        path: Path,
        certificate_chain: Iterable[Certificate],
        key: RSAPrivateKeyWithSerialization,
    ) -> None:
        path.parent.mkdir(mode=0o770, parents=True, exist_ok=True)
        with path.open(mode="wb") as f:
            f.write(self._serialize_private_key(key))
            for cert in certificate_chain:
                f.write(self._serialize_certificate(cert))
        path.chmod(mode=0o660)

    def _write_cert_and_root(
        self,
        path: Path,
        cert: Certificate,
        key: RSAPrivateKeyWithSerialization,
    ) -> None:
        self._write_cert_chain(
            path,
            [cert, self._get_root_certificate()[0]],
            key,
        )

    @property
    def is_initialized(self) -> bool:
        return self._root_cert_path.exists()

    def site_certificate_exists(self, site_id: str) -> bool:
        return self._site_certificate_path(site_id).exists()

    @property
    def marcv_certificate_exists(self) -> bool:
        return self._marcv_cert_path.exists()

    def initialize(self):
        """Initialize the root CA key / certficate in case it does not exist yet"""
        if self.is_initialized:
            return
        root_cert, root_key = self._create_root_certificate()
        self._write_cert_chain(self._root_cert_path, [root_cert], root_key)

    def create_site_certificate(self, site_id: str) -> None:
        """Creates the key / certificate for the given Check_MK site"""
        self._write_cert_and_root(
            self._site_certificate_path(site_id),
            *self._certificate_from_root(site_id),
        )

    def create_marcv_certificate(self) -> None:
        """Creates the key / certificate for marcv server"""
        self._write_cert_and_root(
            self._marcv_cert_path,
            *self._certificate_from_root("localhost"),
        )
