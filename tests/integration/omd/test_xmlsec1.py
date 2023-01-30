#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
from typing import Iterator

import pytest

from tests.testlib.site import Site


class TestXmlsec1:
    @pytest.fixture
    def private_key(self) -> str:
        return """-----BEGIN RSA PRIVATE KEY-----
MIICWgIBAAKBgGtgyn7EtFXGg+atX6dYOZIb9/zLqgzD3BbRiA8rGHSJAjMWIYcJ
ugeFACMtS9xsDk1fjVdzEhC1AUQd6EB2xSuwwUg5n8gzp/NDtmdiI7so2NxjPqwX
AGL1v1EsRGXMg40Z70CE8SYZAEF/HCJhY4DPUXJtK2q2TKXhhBUytpTJAgMBAAEC
gYBhYwzlAqSIMx7IJbBeh07XrFQzS8g0AaNocqtTDoQElYqQKN9JqVG2pjLktJ1c
Egi6thHsIWpeCrxWOkW9ybqy41GFJBA6o+OLiZn7Zd9AklAH9JwzVkpXly7G6vAQ
mEut2AHkwK2AxamHQ/LB6fLp8Te86WmmzyyGteNe3WWnrQJBAK8KQYoB8qT4mcIf
FVCbxNR4rD54gelVlkVFI1EIBxKOXzvkd/D0OIV+WPOCBgGnWOgMuMrlcX1ljmG5
y+q7V68CQQCdCvh7x+1bY3fbR+NDucQGxVBTnZtH3h8c/kW+b3cZCVbe6LDaXvBl
gyuuBvk7CmaEXqF79wssoXvMHgtYGIEHAkAtMj69/cbDZhV9lD0StUXbftUqxD73
GsxUUofN8n6xAeYBNvrpUoYNohQhvB8E6ksAj9hfO2NUd5aOEUVf9MOtAkAtgw1q
ShGWx6fnq9jIOuD9mVdjNCzZUh0wONybiRA5+EPty//c+WCv+qjBAZJfMu9s80PX
ekwJvi7zg82D1W4nAkBoLAwAMxEy6vGJfOwHD4+Wb9PlBULahdt+x2ajT6vuFs7s
OFfDfevFgsxc1hDRMGZe6hPoBEZx25OIHuJEOLox
-----END RSA PRIVATE KEY-----
"""

    @pytest.fixture
    def public_key(self) -> str:
        return """-----BEGIN PUBLIC KEY-----
MIGeMA0GCSqGSIb3DQEBAQUAA4GMADCBiAKBgGtgyn7EtFXGg+atX6dYOZIb9/zL
qgzD3BbRiA8rGHSJAjMWIYcJugeFACMtS9xsDk1fjVdzEhC1AUQd6EB2xSuwwUg5
n8gzp/NDtmdiI7so2NxjPqwXAGL1v1EsRGXMg40Z70CE8SYZAEF/HCJhY4DPUXJt
K2q2TKXhhBUytpTJAgMBAAE=
-----END PUBLIC KEY-----
"""

    @pytest.fixture
    def xml_file_content(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<!--
XML Security Library example: Original XML doc file before encryption (encrypt3 example).
-->
<Envelope xmlns="urn:envelope">
  <Data>
    Hello, World!
  </Data>
</Envelope>
"""

    @pytest.fixture
    def xml_signature_template_content(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<!--
XML Security Library example: Simple signature template file for sign1 example.
-->
<Envelope xmlns="urn:envelope">
  <Data>
    Hello, World!
  </Data>
  <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
    <SignedInfo>
      <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315" />
      <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
      <Reference URI="">
        <Transforms>
          <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature" />
        </Transforms>
        <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
        <DigestValue></DigestValue>
      </Reference>
    </SignedInfo>
    <SignatureValue/>
    <KeyInfo>
        <KeyName/>
    </KeyInfo>
  </Signature>
</Envelope>
"""

    @pytest.fixture
    def xml_encryption_template_content(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<!--
XML Security Library example: Original XML
 doc file before encryption (encrypt3 example).
-->
<EncryptedData
  xmlns="http://www.w3.org/2001/04/xmlenc#"
  Type="http://www.w3.org/2001/04/xmlenc#Element">
 <EncryptionMethod Algorithm=
   "http://www.w3.org/2001/04/xmlenc#tripledes-cbc"/>
 <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
  <EncryptedKey xmlns="http://www.w3.org/2001/04/xmlenc#">
   <EncryptionMethod Algorithm=
     "http://www.w3.org/2001/04/xmlenc#rsa-1_5"/>
   <KeyInfo xmlns="http://www.w3.org/2000/09/xmldsig#">
    <KeyName/>
   </KeyInfo>
   <CipherData>
    <CipherValue/>
   </CipherData>
  </EncryptedKey>
 </KeyInfo>
 <CipherData>
  <CipherValue/>
 </CipherData>
</EncryptedData>

"""

    @pytest.fixture
    def private_key_file(self, site: Site, private_key: str) -> Iterator[str]:
        filepath = f"{os.environ['OMD_ROOT']}/tmp/xmlsec1-test-privatekey.pem"
        site.write_text_file(filepath, private_key)
        yield filepath
        site.delete_file(filepath)

    @pytest.fixture
    def public_key_file(self, site: Site, public_key: str) -> Iterator[str]:
        filepath = f"{os.environ['OMD_ROOT']}/tmp/xmlsec1-test-publickey.pem"
        site.write_text_file(filepath, public_key)
        yield filepath
        site.delete_file(filepath)

    @pytest.fixture
    def xml_file(self, site: Site, xml_file_content: str) -> Iterator[str]:
        filepath = f"{os.environ['OMD_ROOT']}/tmp/xmlsec1-test-example.xml"
        site.write_text_file(filepath, xml_file_content)
        yield filepath
        site.delete_file(filepath)

    @pytest.fixture
    def xml_signature_template(
        self,
        site: Site,
        xml_signature_template_content: str,
    ) -> Iterator[str]:
        filepath = f"{os.environ['OMD_ROOT']}/tmp/xmlsec1-test-signature-template.xml"
        site.write_text_file(filepath, xml_signature_template_content)
        yield filepath
        site.delete_file(filepath)

    @pytest.fixture
    def xml_encryption_template(
        self,
        site: Site,
        xml_encryption_template_content: str,
    ) -> Iterator[str]:
        filepath = f"{os.environ['OMD_ROOT']}/tmp/xmlsec1-test-encryption-template.xml"
        site.write_text_file(filepath, xml_encryption_template_content)
        yield filepath
        site.delete_file(filepath)

    def test_xmlsec1_is_available(self, site: Site) -> None:
        p = site.execute(
            ["xmlsec1", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _stdout, stderr = p.communicate()

        assert p.returncode == 0, f"STDERR: {stderr}"

    def test_xmlsec1_signing(
        self,
        site: Site,
        private_key_file: str,
        xml_file: str,
        xml_signature_template: str,
    ) -> None:
        p = site.execute(
            [
                "xmlsec1",
                "--sign",
                "--privkey-pem",
                private_key_file,
                xml_signature_template,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _stdout, stderr = p.communicate()

        assert p.returncode == 0, f"STDERR: {stderr}"

    def test_xmlsec1_encryption(
        self,
        site: Site,
        public_key_file: str,
        xml_file: str,
        xml_encryption_template: str,
    ) -> None:
        p = site.execute(
            [
                "xmlsec1",
                "--encrypt",
                "--pubkey",
                public_key_file,
                "--session-key",
                "des-192",
                "--xml-data",
                xml_file,
                xml_encryption_template,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _stdout, stderr = p.communicate()

        assert p.returncode == 0, f"STDERR: {stderr}"
