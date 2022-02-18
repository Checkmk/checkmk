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
        self._agent_receiver_cert_path = ca_path / "agent_receiver_cert.pem"

    def _site_certificate_path(self, site_id: str) -> Path:
        return (self._ca_path / "sites" / site_id).with_suffix(".pem")

    def site_certificate_exists(self, site_id: str) -> bool:
        return self._site_certificate_path(site_id).exists()

    @property
    def agent_receiver_certificate_exists(self) -> bool:
        return self._agent_receiver_cert_path.exists()

    def create_site_certificate(self, site_id: str, days_valid: int) -> None:
        """Creates the key / certificate for the given Check_MK site"""
        self.root_ca.save_new_signed_cert(self._site_certificate_path(site_id), site_id, days_valid)

    def create_agent_receiver_certificate(self, days_valid: int) -> None:
        """Creates the key / certificate for agent-receiver server"""
        self.root_ca.save_new_signed_cert(self._agent_receiver_cert_path, "localhost", days_valid)
