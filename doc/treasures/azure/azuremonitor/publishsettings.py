# Copyright 2013 MS Open Tech
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#publishsettings.py: PublishSettings class

import OpenSSL.crypto
import base64
import os
import tempfile
import xml.dom.minidom

"""Contains the PublishSettings class."""

class PublishSettings:
    """Class to represent a Windows Azure .publishsettings file"""
    sub_id = None
    pkcs12_buf = None

    def __init__(self, ps_file):
        """Parse the ps file and save the info in the object."""
        ps_doc = xml.dom.minidom.parse(ps_file)
        publish_data = ps_doc.getElementsByTagName('PublishData')[0]
        publish_prof = publish_data.getElementsByTagName('PublishProfile')[0]
        schema_version = publish_prof.getAttribute('SchemaVersion')
        sub = publish_prof.getElementsByTagName('Subscription')[0]
        self.sub_id = sub.getAttribute('Id')
        if not schema_version:
            pkcs12_b64 = publish_prof.getAttribute('ManagementCertificate')
        else:
            pkcs12_b64 = sub.getAttribute('ManagementCertificate')
        self.pkcs12_buf = base64.b64decode(pkcs12_b64)

    def write_pem(self, location=None):
        """Write the management certificate to a .pem file.

        location -- If specified, write pem to that location
                    Otherwise, write to a temp file
        Returns the full path of the file written.
        """
        pkcs12 = OpenSSL.crypto.load_pkcs12(self.pkcs12_buf)
        cert = pkcs12.get_certificate()
        private_key = pkcs12.get_privatekey()
        cert_pem = OpenSSL.crypto.dump_certificate(
            OpenSSL.crypto.FILETYPE_PEM, cert)
        pkey_pem = OpenSSL.crypto.dump_privatekey(
            OpenSSL.crypto.FILETYPE_PEM, private_key)
        pem_file = None
        if location is None:
            (pem_fd, location) = tempfile.mkstemp()
            pem_file = os.fdopen(pem_fd, 'w')
        else:
            #open location
            raise NotImplementedError
        pem_file.write(pkey_pem)
        pem_file.write(cert_pem)
        pem_file.close
        return location
