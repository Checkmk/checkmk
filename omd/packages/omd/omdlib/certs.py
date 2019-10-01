#!/usr/bin/env python
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

import sys
from typing import Tuple  # pylint: disable=unused-import
import random
# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path
from OpenSSL import crypto
from OpenSSL.SSL import FILETYPE_PEM  # type: ignore

CERT_NOT_AFTER = 999 * 365 * 24 * 60 * 60  # 999 years by default
CA_CERT_NOT_AFTER = CERT_NOT_AFTER


class CertificateAuthority(object):
    """Management of the site local CA and certificates issued by it"""
    def __init__(self, ca_path, ca_name):
        # type: (Path, str) -> None
        super(CertificateAuthority, self).__init__()
        self._ca_path = ca_path
        self._ca_name = ca_name

    @property
    def ca_path(self):
        return self._ca_path

    @property
    def _root_cert_path(self):
        return self.ca_path / "ca.pem"

    @property
    def is_initialized(self):
        # type: () -> bool
        return self._root_cert_path.exists()

    def initialize(self):
        """Initialize the root CA key / certficate in case it does not exist yet"""
        if self.is_initialized:
            return
        root_cert, root_key = self._create_root_certificate()
        self._write_pem(self._root_cert_path, [root_cert], root_key)

    def _create_root_certificate(self):
        # type: () -> Tuple[crypto.PKey, str]
        key = self._make_private_key()

        cert = self._make_cert(self._ca_name, CA_CERT_NOT_AFTER)
        cert.set_issuer(cert.get_subject())
        cert.set_pubkey(key)
        cert.add_extensions([
            crypto.X509Extension(b"subjectKeyIdentifier", False, b"hash", subject=cert),
            crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE, pathlen:0"),
            crypto.X509Extension(b"keyUsage", True, b"keyCertSign, cRLSign"),
        ])
        cert.sign(key, "sha512")

        return cert, key

    def _get_root_certificate(self):
        # type: () -> Tuple[str, str]
        return self._read_pem(self._root_cert_path)

    def site_certificate_exists(self, site_id):
        # type: (str) -> bool
        return self.site_certificate_path(site_id).exists()

    def read_site_certificate(self, site_id):
        # type: (str) -> Tuple[crypto.X509, crypto.PKey]
        return self._read_pem(self.site_certificate_path(site_id))

    def create_site_certificate(self, site_id):
        # type: (str) -> None
        """Creates the key / certificate for the given Check_MK site"""
        if not self.is_initialized:
            raise Exception("Certificate authority is not initialized yet")

        root_cert, root_key = self._get_root_certificate()

        key = self._make_private_key()

        req = crypto.X509Req()
        req.get_subject().CN = site_id
        req.set_pubkey(key)
        req.sign(key, "sha512")

        cert = self._make_cert(site_id, CERT_NOT_AFTER)

        cert.set_issuer(root_cert.get_subject())
        cert.set_pubkey(req.get_pubkey())

        cert.sign(root_key, "sha512")

        self.write_site_certificate(site_id, cert, key)

    def write_site_certificate(self, site_id, cert, key):
        # type: (str, crypto.X509, crypto.PKey) -> None
        certificate_chain = [cert, self._get_root_certificate()[0]]
        self._write_pem(self.site_certificate_path(site_id), certificate_chain, key)

    def site_certificate_path(self, site_id):
        # type: (str) -> Path
        return (self.ca_path / "sites" / site_id).with_suffix(".pem")

    def _make_cert(self, cn, not_after):
        # type: (str, int) -> crypto.X509

        cert = crypto.X509()
        cert.set_serial_number(random.randint(0, sys.maxsize))
        cert.set_version(2)
        cert.get_subject().CN = cn

        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(not_after)

        return cert

    def _make_private_key(self):
        # type: () -> crypto.PKey
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 2048)
        return key

    def _write_pem(self, path, certificate_chain, key):
        # type: (Path, List[crypto.X509], crypto.PKey) -> None
        path.parent.mkdir(mode=0o770, parents=True, exist_ok=True)
        with path.open(mode="wb") as f:
            f.write(crypto.dump_privatekey(FILETYPE_PEM, key))
            for cert in certificate_chain:
                f.write(crypto.dump_certificate(FILETYPE_PEM, cert))
        path.chmod(mode=0o660)

    def _read_pem(self, path):
        # type: (Path) -> Tuple[crypto.X509, crypto.PKey]
        with path.open(mode="rb") as f:
            file_contents = f.read()
            cert = crypto.load_certificate(FILETYPE_PEM, file_contents)
            key = crypto.load_privatekey(FILETYPE_PEM, file_contents)
        return cert, key
