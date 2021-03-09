# *--encoding: UTF-8--*
# yapf: disable
# pylint: disable=too-many-lines
# pylint: disable=line-too-long
# pylint: disable=invalid-name
import os
import re
import pytest

pytestmark = pytest.mark.checks

regex = re.compile

execfile(os.path.join(os.path.dirname(__file__), '../../../checks/legacy_docker.include'))

REQUIRED_IMAGE_KEYS = (
    ("Id", (str, unicode)),
    ("RepoTags", list),
    ("Created", (str, unicode)),
    ("VirtualSize", int),
    ("Labels", dict),
    ("amount_containers", int),
)

REQUIRED_CONTAINER_KEYS = (
    ("Id", (str, unicode)),
    ("Image", (str, unicode)),
    ("Created", (str, unicode)),
    ("Labels", dict),
    ("Name", (str, unicode)),
    ("Status", (str, unicode)),
)

SUBSECTIONS1 = {
    'images': [
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '11:13:11', '+0200',
            'CEST","CreatedSince":"5', 'hours',
            'ago","Digest":"\u003cnone\u003e","ID":"ed55e8b95336","Repository":"local/c7-systemd-httpd","SharedSize":"N/A","Size":"254MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"254.2MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '11:12:15', '+0200',
            'CEST","CreatedSince":"5', 'hours',
            'ago","Digest":"\u003cnone\u003e","ID":"6c97da45403a","Repository":"local/c7-systemd","SharedSize":"N/A","Size":"200MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"199.7MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-10', '08:40:21', '+0200',
            'CEST","CreatedSince":"2', 'days',
            'ago","Digest":"\u003cnone\u003e","ID":"ed5d6b154e97","Repository":"docker-tests/check-mk-enterprise-master-2018.10.10","SharedSize":"N/A","Size":"844MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"844.3MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-10', '08:37:26', '+0200',
            'CEST","CreatedSince":"2', 'days',
            'ago","Digest":"\u003cnone\u003e","ID":"df118e583614","Repository":"docker-tests/check-mk-enterprise-master-1.5.0p5","SharedSize":"N/A","Size":"818MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"817.6MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-28', '23:54:16', '+0200',
            'CEST","CreatedSince":"13', 'days',
            'ago","Digest":"\u003cnone\u003e","ID":"4a77be28f8e5","Repository":"checkmk/check-mk-raw","SharedSize":"N/A","Size":"752MB","Tag":"1.5.0p5","UniqueSize":"N/A","VirtualSize":"751.9MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-17', '09:47:56', '+0200',
            'CEST","CreatedSince":"3', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"f4bfbb70768f","Repository":"docker-tests/check-mk-enterprise-master-1.5.0p3","SharedSize":"N/A","Size":"817MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"817.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-17', '09:45:08', '+0200',
            'CEST","CreatedSince":"3', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"ff19a3911e0a","Repository":"docker-tests/check-mk-enterprise-master-2018.09.17","SharedSize":"N/A","Size":"831MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '16:52:00', '+0200',
            'CEST","CreatedSince":"3', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"c0582f734ad1","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"831MB","Tag":"2018.09.14","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '14:47:41', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"91152cc1c4bc","Repository":"docker-tests/check-mk-enterprise-master-2018.09.14","SharedSize":"N/A","Size":"831MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '13:08:54', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"8ca14ae84dd9","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"972MB","Tag":"daily","UniqueSize":"N/A","VirtualSize":"972.3MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '12:45:50', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"44a5d6d15272","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"818MB","Tag":"1.5.0-2018.09.14","UniqueSize":"N/A","VirtualSize":"818MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '12:45:50', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"44a5d6d15272","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"818MB","Tag":"1.5.0-daily","UniqueSize":"N/A","VirtualSize":"818MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-13', '08:27:42', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"2e89feac7533","Repository":"docker-tests/check-mk-enterprise-master-2018.09.13","SharedSize":"N/A","Size":"831MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-13', '08:15:30', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"096300fde75d","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"818MB","Tag":"1.5.0-2018.09.13","UniqueSize":"N/A","VirtualSize":"818MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-12', '21:15:47', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"8d463a5f7635","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"815MB","Tag":"1.5.0-2018.09.12","UniqueSize":"N/A","VirtualSize":"814.9MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-12', '19:49:54', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"a1f15f9a2b16","Repository":"docker-tests/check-mk-enterprise-master-2018.09.12","SharedSize":"N/A","Size":"828MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"828.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-12', '09:33:22', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"ee5124a3adb5","Repository":"docker-tests/check-mk-enterprise-master-2018.09.11","SharedSize":"N/A","Size":"828MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"828.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-10', '17:36:25', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"6143303a8e14","Repository":"hadolint/hadolint","SharedSize":"N/A","Size":"3.64MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"3.645MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-04', '23:21:34', '+0200',
            'CEST","CreatedSince":"5', 'weeks',
            'ago","Digest":"\u003cnone\u003e","ID":"44e19a16bde1","Repository":"debian","SharedSize":"N/A","Size":"55.3MB","Tag":"stretch-slim","UniqueSize":"N/A","VirtualSize":"55.27MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-08-06', '21:21:48', '+0200',
            'CEST","CreatedSince":"2', 'months',
            'ago","Digest":"\u003cnone\u003e","ID":"5182e96772bf","Repository":"centos","SharedSize":"N/A","Size":"200MB","Tag":"7","UniqueSize":"N/A","VirtualSize":"199.7MB"}'
        ]
    ],
    'image_labels': [
        [
            '[', '"sha256:ed55e8b953366b628773629b98dba9adc07a9c1543efbb04c18f0052e26ee719",',
            '{"org.label-schema.build-date":"20180804","org.label-schema.license":"GPLv2","org.label-schema.name":"CentOS',
            'Base',
            'Image","org.label-schema.schema-version":"1.0","org.label-schema.vendor":"CentOS"}',
            ']'
        ],
        [
            '[', '"sha256:6c97da45403ae758af1cbc5a2480d5d5e8882c41a554eadc35e48769d641b15e",',
            '{"org.label-schema.build-date":"20180804","org.label-schema.license":"GPLv2","org.label-schema.name":"CentOS',
            'Base',
            'Image","org.label-schema.schema-version":"1.0","org.label-schema.vendor":"CentOS"}',
            ']'
        ],
        [
            '[', '"sha256:ed5d6b154e9754577224bc7f57e893f899664d4b0b336157063a714877024930",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.10.10"}', ']'
        ],
        [
            '[', '"sha256:df118e583614f41d5f190ced1a344ee3ccce2c36e91caf795d78e3c01d906701",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0p5"}', ']'
        ],
        [
            '[', '"sha256:4a77be28f8e54a4e6a8ecd8cfbd1963463d1e7ac719990206ced057af41e9957",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0p5"}', ']'
        ],
        [
            '[', '"sha256:f4bfbb70768f233f1adca8e9e7333695a263773c2663a97732519f3e0eed87b7",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0p3"}', ']'
        ],
        [
            '[', '"sha256:ff19a3911e0a1560a945c4d749cb47ffd1ca9397f506d195ae8d30a86f46807e",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.17"}', ']'
        ],
        [
            '[', '"sha256:c0582f734ad1bb8c9adaf014c6d0b90ec532bf137afcdb4afe304c0c581ed308",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:91152cc1c4bcd3aba6309d88b2c2a7e53f2e6209757f3fda180489f064994287",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:8ca14ae84dd9a788bcaddd196cbed346d6cd624fa1a63253728df769e26d2a21",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:44a5d6d152722adef8dada252863f178993d955b49caa8ea7b954d9ebc93b1c2",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0-2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:44a5d6d152722adef8dada252863f178993d955b49caa8ea7b954d9ebc93b1c2",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0-2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:2e89feac75330553688011dfb2efc0f9c6e44b61a419d937ad826c8628007e10",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.13"}', ']'
        ],
        [
            '[', '"sha256:096300fde75dddfb273b343aa94957dffdbb4b57212debaddbd6f7714442df57",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0-2018.09.13"}', ']'
        ],
        [
            '[', '"sha256:8d463a5f7635ebd0c6f418236c571273083e1c5bc63711a2babc4048208f9aa3",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0-2018.09.12"}', ']'
        ],
        [
            '[', '"sha256:a1f15f9a2b1640ac73437fc96b658b7c9907ab14127e1ec82cd93986874e3159",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.12"}', ']'
        ],
        [
            '[', '"sha256:ee5124a3adb5eb20012a7189ea34495da3e39ff8517c2c260954654d3edf1553",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.11"}', ']'
        ],
        [
            '[', '"sha256:6143303a8e14d19961946d8749b698e2d1a90262c62a11dee5a40367907afe88",',
            'null', ']'
        ],
        [
            '[', '"sha256:44e19a16bde1fd0f00b8cfb2b816e329ddee5c79869d140415f4445df4da485c",',
            'null', ']'
        ],
        [
            '[', '"sha256:5182e96772bf11f4b912658e265dfe0db8bd314475443b6434ea708784192892",',
            '{"org.label-schema.build-date":"20180804","org.label-schema.license":"GPLv2","org.label-schema.name":"CentOS',
            'Base',
            'Image","org.label-schema.schema-version":"1.0","org.label-schema.vendor":"CentOS"}',
            ']'
        ]
    ],
    'containers': [
        [
            '{"Command":"\\"/usr/sbin/init\\"","CreatedAt":"2018-10-12', '11:13:24', '+0200',
            'CEST","ID":"f1641e401237","Image":"local/c7-systemd-httpd","Labels":"org.label-schema.build-date=20180804,org.label-schema.license=GPLv2,org.label-schema.name=CentOS',
            'Base', 'Image,org.label-schema.schema-version=1.0,funny.value.with.commas=This', 'is',
            'really,', 'really',
            'stupid.,org.label-schema.vendor=CentOS","LocalVolumes":"0","Mounts":"/sys/fs/cgroup","Names":"sad_stonebraker","Networks":"bridge","Ports":"0.0.0.0:8080-\u003e80/tcp","RunningFor":"5',
            'hours', 'ago","Size":"0B","Status":"Up', '5', 'hours"}'
        ],
        [
            '{"Command":"\\"/usr/sbin/init\\"","CreatedAt":"2018-10-12', '11:13:18', '+0200',
            'CEST","ID":"7d32581dd10f","Image":"local/c7-systemd-httpd","Labels":"org.label-schema.vendor=CentOS,org.label-schema.build-date=20180804,org.label-schema.license=GPLv2,org.label-schema.name=CentOS',
            'Base',
            'Image,org.label-schema.schema-version=1.0","LocalVolumes":"0","Mounts":"/sys/fs/cgroup","Names":"sad_austin","Networks":"bridge","Ports":"","RunningFor":"5',
            'hours', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.…\\"","CreatedAt":"2018-10-12', '09:17:54', '+0200',
            'CEST","ID":"fdd04795069e","Image":"checkmk/check-mk-raw:1.5.0p5","Labels":"org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com","LocalVolumes":"1","Mounts":"/etc/localtime,10b7c962177bf2…","Names":"monitoringx","Networks":"bridge","Ports":"","RunningFor":"7',
            'hours', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.…\\"","CreatedAt":"2018-10-10', '08:40:21', '+0200',
            'CEST","ID":"b17185d5dcc5","Image":"94f49a7afedb","Labels":"org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk","LocalVolumes":"0","Mounts":"","Names":"friendly_banach","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:40:20',
            '+0200',
            'CEST","ID":"73237ecc5183","Image":"d27276979703","Labels":"org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk","LocalVolumes":"0","Mounts":"","Names":"festive_stallman","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:40:20',
            '+0200',
            'CEST","ID":"0d7e34ebb911","Image":"03d98e475cd6","Labels":"maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10","LocalVolumes":"0","Mounts":"","Names":"youthful_pare","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:40:20',
            '+0200',
            'CEST","ID":"580a7b4bd20a","Image":"3e0dd44b22e4","Labels":"org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk","LocalVolumes":"0","Mounts":"","Names":"reverent_proskuriakova","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'set', '-e', '…\\"","CreatedAt":"2018-10-10',
            '08:39:29', '+0200',
            'CEST","ID":"4a6806b168b1","Image":"089108b69108","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"festive_fermi","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '2', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'set', '-e', '…\\"","CreatedAt":"2018-10-10',
            '08:37:43', '+0200',
            'CEST","ID":"93e0c88a69fa","Image":"b16a30c66821","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"objective_darwin","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '2', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.…\\"","CreatedAt":"2018-10-10', '08:37:26', '+0200',
            'CEST","ID":"6fe73b950209","Image":"d4c95e27986c","Labels":"org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk","LocalVolumes":"0","Mounts":"","Names":"admiring_haibt","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:37:26',
            '+0200',
            'CEST","ID":"bfdb64ccf0ba","Image":"21b2f3d5e6c0","Labels":"org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\u0026', 'Application',
            'Monitoring","LocalVolumes":"0","Mounts":"","Names":"lucid_bohr","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:37:25',
            '+0200',
            'CEST","ID":"24772268cc09","Image":"6e66f5473958","Labels":"maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5","LocalVolumes":"0","Mounts":"","Names":"zen_bartik","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:37:25',
            '+0200',
            'CEST","ID":"8f8ded35fc90","Image":"6bccd8c3ed71","Labels":"org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH","LocalVolumes":"0","Mounts":"","Names":"keen_cori","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'set', '-e', '…\\"","CreatedAt":"2018-10-10',
            '08:36:45', '+0200',
            'CEST","ID":"a073bb9adfbe","Image":"7aa4b82c92ae","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"jovial_archimedes","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '2', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'set', '-e', '…\\"","CreatedAt":"2018-10-10',
            '08:34:58', '+0200',
            'CEST","ID":"4d4d9f3be74b","Image":"b16a30c66821","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"pensive_spence","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '2', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:58',
            '+0200',
            'CEST","ID":"df44340ed121","Image":"1b013e043efa","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"unruffled_hopper","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:58',
            '+0200',
            'CEST","ID":"860d8dfff4f6","Image":"7e7f944ba518","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"dazzling_meninsky","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:57',
            '+0200',
            'CEST","ID":"a17f21f95383","Image":"a2a187fcaa76","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"serene_poincare","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:57',
            '+0200',
            'CEST","ID":"6cae82f879ff","Image":"1d9b21b9e019","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"elated_poitras","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:57',
            '+0200',
            'CEST","ID":"aad80d524200","Image":"e002e37aec84","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"competent_keller","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:56',
            '+0200',
            'CEST","ID":"d1c70f4690b5","Image":"0b5da1249a04","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"trusting_panini","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:56',
            '+0200',
            'CEST","ID":"9b08cf26da8c","Image":"164429e47a3f","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"pensive_swartz","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:56',
            '+0200',
            'CEST","ID":"c04099ed3f18","Image":"d1a41c564864","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"dreamy_thompson","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:56',
            '+0200',
            'CEST","ID":"cdc7e1e4a24e","Image":"999fc035fc76","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"lucid_brown","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:55',
            '+0200',
            'CEST","ID":"10d6b884f348","Image":"a0a951b126eb","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"wizardly_ritchie","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:55',
            '+0200',
            'CEST","ID":"d37198a74c08","Image":"caac4aa6ac57","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"distracted_mccarthy","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', '\'#(nop)', '…\\"","CreatedAt":"2018-10-10', '08:34:55',
            '+0200',
            'CEST","ID":"55632dca94c8","Image":"1919d446eafa","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"stoic_perlman","Networks":"bridge","Ports":"","RunningFor":"2',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/bash\"","CreatedAt":"2018-09-27', '19:06:07', '+0200',
            'CEST","ID":"85a41e54b0cc","Image":"centos:7","Labels":"org.label-schema.license=GPLv2,org.label-schema.name=CentOS',
            'Base',
            'Image,org.label-schema.schema-version=1.0,org.label-schema.vendor=CentOS,org.label-schema.build-date=20180804","LocalVolumes":"0","Mounts":"","Names":"vigorous_pare","Networks":"bridge","Ports":"","RunningFor":"2',
            'weeks', 'ago","Size":"0B","Status":"Exited', '(137)', '2', 'weeks', 'ago"}'
        ]
    ],
}

EXPECTED_IMAGES1 = {
    u'096300fde75d': {
        u'Created': u'2018-09-13 08:15:30 +0200 CEST',
        u'RepoTags': [u'checkmk/check-mk-enterprise:1.5.0-2018.09.13'],
        u'VirtualSize': 818000000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "1.5.0-2018.09.13",
        },
    },
    u'2e89feac7533': {
        u'Created': u'2018-09-13 08:27:42 +0200 CEST',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-2018.09.13:latest'],
        u'VirtualSize': 831400000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "2018.09.13"
        },
    },
    u'44a5d6d15272': {
        u'Created': u'2018-09-14 12:45:50 +0200 CEST',
        u'RepoTags': [u'checkmk/check-mk-enterprise:1.5.0-daily'],
        u'VirtualSize': 818000000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "1.5.0-2018.09.14"
        },
    },
    u'44e19a16bde1': {
        u'Created': u'2018-09-04 23:21:34 +0200 CEST',
        u'RepoTags': ['debian:stretch-slim'],
        u'VirtualSize': 55270000,
        u'amount_containers': 0,
    },
    u'4a77be28f8e5': {
        u'Created': u'2018-09-28 23:54:16 +0200 CEST',
        u'RepoTags': ['checkmk/check-mk-raw:1.5.0p5'],
        u'VirtualSize': 751900000,
        u'amount_containers': 1,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "1.5.0p5"
        },
    },
    u'5182e96772bf': {
        u'Created': u'2018-08-06 21:21:48 +0200 CEST',
        u'RepoTags': ['centos:7'],
        u'VirtualSize': 199700000,
        u'amount_containers': 0,
        u'Labels': {
            "org.label-schema.build-date": "20180804",
            "org.label-schema.license": "GPLv2",
            "org.label-schema.name": "CentOS Base Image",
            "org.label-schema.schema-version": "1.0",
            "org.label-schema.vendor": "CentOS"
        },
    },
    u'6143303a8e14': {
        u'Created': u'2018-09-10 17:36:25 +0200 CEST',
        u'RepoTags': ['hadolint/hadolint:latest'],
        u'VirtualSize': 3645000,
        u'amount_containers': 0,
    },
    u'6c97da45403a': {
        u'Created': u'2018-10-12 11:12:15 +0200 CEST',
        u'RepoTags': ['local/c7-systemd:latest'],
        u'VirtualSize': 199700000,
        u'amount_containers': 0,
        u'Labels': {
            "org.label-schema.build-date": "20180804",
            "org.label-schema.license": "GPLv2",
            "org.label-schema.name": "CentOS Base Image",
            "org.label-schema.schema-version": "1.0",
            "org.label-schema.vendor": "CentOS"
        },
    },
    u'8ca14ae84dd9': {
        u'Created': u'2018-09-14 13:08:54 +0200 CEST',
        u'RepoTags': ['checkmk/check-mk-enterprise:daily'],
        u'VirtualSize': 972300000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "2018.09.14"
        },
    },
    u'8d463a5f7635': {
        u'Created': u'2018-09-12 21:15:47 +0200 CEST',
        u'RepoTags': ['checkmk/check-mk-enterprise:1.5.0-2018.09.12'],
        u'VirtualSize': 814900000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "1.5.0-2018.09.12"
        },
    },
    u'91152cc1c4bc': {
        u'Created': u'2018-09-14 14:47:41 +0200 CEST',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-2018.09.14:latest'],
        u'VirtualSize': 831400000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "2018.09.14"
        },
    },
    u'a1f15f9a2b16': {
        u'Created': u'2018-09-12 19:49:54 +0200 CEST',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-2018.09.12:latest'],
        u'VirtualSize': 828400000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "2018.09.12"
        },
    },
    u'c0582f734ad1': {
        u'Created': u'2018-09-14 16:52:00 +0200 CEST',
        u'RepoTags': ['checkmk/check-mk-enterprise:2018.09.14'],
        u'VirtualSize': 831400000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "2018.09.14"
        },
    },
    u'df118e583614': {
        u'Created': u'2018-10-10 08:37:26 +0200 CEST',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-1.5.0p5:latest'],
        u'VirtualSize': 817600000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "1.5.0p5"
        },
    },
    u'ed55e8b95336': {
        u'Created': u'2018-10-12 11:13:11 +0200 CEST',
        u'RepoTags': ['local/c7-systemd-httpd:latest'],
        u'VirtualSize': 254200000,
        u'amount_containers': 2,
        u'Labels': {
            "org.label-schema.build-date": "20180804",
            "org.label-schema.license": "GPLv2",
            "org.label-schema.name": "CentOS Base Image",
            "org.label-schema.schema-version": "1.0",
            "org.label-schema.vendor": "CentOS"
        },
    },
    u'ed5d6b154e97': {
        u'Created': u'2018-10-10 08:40:21 +0200 CEST',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-2018.10.10:latest'],
        u'VirtualSize': 844300000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "2018.10.10"
        },
    },
    u'ee5124a3adb5': {
        u'Created': u'2018-09-12 09:33:22 +0200 CEST',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-2018.09.11:latest'],
        u'VirtualSize': 828400000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "2018.09.11"
        },
    },
    u'f4bfbb70768f': {
        u'Created': u'2018-09-17 09:47:56 +0200 CEST',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-1.5.0p3:latest'],
        u'VirtualSize': 817400000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "1.5.0p3"
        },
    },
    u'ff19a3911e0a': {
        u'Created': u'2018-09-17 09:45:08 +0200 CEST',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-2018.09.17:latest'],
        u'VirtualSize': 831400000,
        u'amount_containers': 0,
        u'Labels': {
            "maintainer": "feedback@checkmk.com",
            "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
            "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
            "org.opencontainers.image.title": "Checkmk",
            "org.opencontainers.image.url": "https://checkmk.com/",
            "org.opencontainers.image.vendor": "tribe29 GmbH",
            "org.opencontainers.image.version": "2018.09.17"
        },
    },
}

EXPECTED_CONTAINERS1 = {
    u'0d7e34ebb911': {
        u'Created': u'2018-10-10 08:40:20 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.10.10'
        },
        u'Name': u'youthful_pare',
        u'Status': u'Created',
    },
    u'10d6b884f348': {
        u'Created': u'2018-10-10 08:34:55 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'wizardly_ritchie',
        u'Status': u'Created',
    },
    u'24772268cc09': {
        u'Created': u'2018-10-10 08:37:25 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'Name': u'zen_bartik',
        u'Status': u'Created',
    },
    u'4a6806b168b1': {
        u'Created': u'2018-10-10 08:39:29 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'festive_fermi',
        u'Status': u'Exited (0) 2 days ago',
    },
    u'4d4d9f3be74b': {
        u'Created': u'2018-10-10 08:34:58 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'pensive_spence',
        u'Status': u'Exited (0) 2 days ago',
    },
    u'55632dca94c8': {
        u'Created': u'2018-10-10 08:34:55 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'stoic_perlman',
        u'Status': u'Created',
    },
    u'580a7b4bd20a': {
        u'Created': u'2018-10-10 08:40:20 +0200 CEST',
        u'Labels': {
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.10.10',
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk'
        },
        u'Name': u'reverent_proskuriakova',
        u'Status': u'Created',
    },
    u'6cae82f879ff': {
        u'Created': u'2018-10-10 08:34:57 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'elated_poitras',
        u'Status': u'Created',
    },
    u'6fe73b950209': {
        u'Created': u'2018-10-10 08:37:26 +0200 CEST',
        u'Labels': {
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5',
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk'
        },
        u'Name': u'admiring_haibt',
        u'Status': u'Created',
    },
    u'73237ecc5183': {
        u'Created': u'2018-10-10 08:40:20 +0200 CEST',
        u'Labels': {
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.10.10',
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk'
        },
        u'Name': u'festive_stallman',
        u'Status': u'Created',
    },
    u'7d32581dd10f': {
        u'Created': u'2018-10-12 11:13:18 +0200 CEST',
        u'Labels': {
            u'org.label-schema.vendor': u'CentOS',
            u'org.label-schema.build-date': u'20180804',
            u'org.label-schema.license': u'GPLv2',
            u'org.label-schema.name': u'CentOS Base Image',
            u'org.label-schema.schema-version': u'1.0'
        },
        u'Name': u'sad_austin',
        u'Status': u'Created',
    },
    u'860d8dfff4f6': {
        u'Created': u'2018-10-10 08:34:58 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'dazzling_meninsky',
        u'Status': u'Created',
    },
    u'8f8ded35fc90': {
        u'Created': u'2018-10-10 08:37:25 +0200 CEST',
        u'Labels': {
            u'org.opencontainers.image.version': u'1.5.0p5',
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH'
        },
        u'Name': u'keen_cori',
        u'Status': u'Created',
    },
    u'93e0c88a69fa': {
        u'Created': u'2018-10-10 08:37:43 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'objective_darwin',
        u'Status': u'Exited (0) 2 days ago',
    },
    u'9b08cf26da8c': {
        u'Created': u'2018-10-10 08:34:56 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'pensive_swartz',
        u'Status': u'Created',
    },
    u'a073bb9adfbe': {
        u'Created': u'2018-10-10 08:36:45 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'jovial_archimedes',
        u'Status': u'Exited (0) 2 days ago',
    },
    u'a17f21f95383': {
        u'Created': u'2018-10-10 08:34:57 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'serene_poincare',
        u'Status': u'Created',
    },
    u'aad80d524200': {
        u'Created': u'2018-10-10 08:34:57 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'competent_keller',
        u'Status': u'Created',
    },
    u'b17185d5dcc5': {
        u'Created': u'2018-10-10 08:40:21 +0200 CEST',
        u'Labels': {
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.10.10',
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk'
        },
        u'Name': u'friendly_banach',
        u'Status': u'Created',
    },
    u'bfdb64ccf0ba': {
        u'Created': u'2018-10-10 08:37:26 +0200 CEST',
        u'Labels': {
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5',
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring'
        },
        u'Name': u'lucid_bohr',
        u'Status': u'Created',
    },
    u'c04099ed3f18': {
        u'Created': u'2018-10-10 08:34:56 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'dreamy_thompson',
        u'Status': u'Created',
    },
    u'cdc7e1e4a24e': {
        u'Created': u'2018-10-10 08:34:56 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'lucid_brown',
        u'Status': u'Created',
    },
    u'd1c70f4690b5': {
        u'Created': u'2018-10-10 08:34:56 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'trusting_panini',
        u'Status': u'Created',
    },
    u'd37198a74c08': {
        u'Created': u'2018-10-10 08:34:55 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'distracted_mccarthy',
        u'Status': u'Created',
    },
    u'df44340ed121': {
        u'Created': u'2018-10-10 08:34:58 +0200 CEST',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'unruffled_hopper',
        u'Status': u'Created',
    },
    u'f1641e401237': {
        u'Created': u'2018-10-12 11:13:24 +0200 CEST',
        u'Labels': {
            u'org.label-schema.build-date': u'20180804',
            u'org.label-schema.license': u'GPLv2',
            u'org.label-schema.name': u'CentOS Base Image',
            u'funny.value.with.commas': u'This is really, really stupid.',
            u'org.label-schema.schema-version': u'1.0',
            u'org.label-schema.vendor': u'CentOS'
        },
        u'Name': u'sad_stonebraker',
        u'Status': u'Up 5 hours',
    },
    u'fdd04795069e': {
        u'Created': u'2018-10-12 09:17:54 +0200 CEST',
        u'Labels': {
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5',
            u'maintainer': u'feedback@checkmk.com'
        },
        u'Name': u'monitoringx',
        u'Status': u'Created',
    }
}

SUBSECTIONS2 = {
    'images': [
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '16:12:03', '+0200',
            'CEST","CreatedSince":"3', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"485933207afd","Repository":"docker-tests/check-mk-enterprise-master-1.5.0p5"'
            ',"SharedSize":"N/A","Size":"818MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"817.6MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '16:07:29', '+0200',
            'CEST","CreatedSince":"3', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"0983f5184ce7","Repository":"\\u003cnone\\u003e","SharedSize":"N/A","Size":"312MB","Tag":"\\u003cnone\\u003e","UniqueSize":"N/A","VirtualSize":"312.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '11:13:11', '+0200',
            'CEST","CreatedSince":"4', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"ed55e8b95336","Repository":"local/c7-systemd-httpd","SharedSize":"N/A","Size":"254MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"254.2MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '11:12:15', '+0200',
            'CEST","CreatedSince":"4', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"6c97da45403a","Repository":"local/c7-systemd","SharedSize":"N/A","Size":"200MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"199.7MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-10', '08:40:21', '+0200',
            'CEST","CreatedSince":"6', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"ed5d6b154e97","Repository":"docker-tests/check-mk-enterprise-master-2018.10.10","SharedSize":"N/A","Size":"844MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"844.3MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-10', '08:37:26', '+0200',
            'CEST","CreatedSince":"6', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"df118e583614","Repository":"\\u003cnone\\u003e","SharedSize":"N/A","Size":"818MB","Tag":"\\u003cnone\\u003e","UniqueSize":"N/A","VirtualSize":"817.6MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-28', '23:54:16', '+0200',
            'CEST","CreatedSince":"2', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"4a77be28f8e5","Repository":"checkmk/check-mk-raw","SharedSize":"N/A","Size":"752MB","Tag":"1.5.0p5","UniqueSize":"N/A","VirtualSize":"751.9MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-17', '09:47:56', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"f4bfbb70768f","Repository":"docker-tests/check-mk-enterprise-master-1.5.0p3","SharedSize":"N/A","Size":"817MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"817.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-17', '09:45:08', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"ff19a3911e0a","Repository":"docker-tests/check-mk-enterprise-master-2018.09.17","SharedSize":"N/A","Size":"831MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '16:52:00', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"c0582f734ad1","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"831MB","Tag":"2018.09.14","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '14:47:41', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"91152cc1c4bc","Repository":"docker-tests/check-mk-enterprise-master-2018.09.14","SharedSize":"N/A","Size":"831MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '13:08:54', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"8ca14ae84dd9","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"972MB","Tag":"daily","UniqueSize":"N/A","VirtualSize":"972.3MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '12:45:50', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"44a5d6d15272","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"818MB","Tag":"1.5.0-2018.09.14","UniqueSize":"N/A","VirtualSize":"818MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '12:45:50', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"44a5d6d15272","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"818MB","Tag":"1.5.0-daily","UniqueSize":"N/A","VirtualSize":"818MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-13', '08:27:42', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"2e89feac7533","Repository":"docker-tests/check-mk-enterprise-master-2018.09.13","SharedSize":"N/A","Size":"831MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-13', '08:15:30', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"096300fde75d","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"818MB","Tag":"1.5.0-2018.09.13","UniqueSize":"N/A","VirtualSize":"818MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-12', '21:15:47', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"8d463a5f7635","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"815MB","Tag":"1.5.0-2018.09.12","UniqueSize":"N/A","VirtualSize":"814.9MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-12', '19:49:54', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"a1f15f9a2b16","Repository":"docker-tests/check-mk-enterprise-master-2018.09.12","SharedSize":"N/A","Size":"828MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"828.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-12', '09:33:22', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"ee5124a3adb5","Repository":"docker-tests/check-mk-enterprise-master-2018.09.11","SharedSize":"N/A","Size":"828MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"828.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-10', '17:36:25', '+0200',
            'CEST","CreatedSince":"5', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"6143303a8e14","Repository":"hadolint/hadolint","SharedSize":"N/A","Size":"3.64MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"3.645MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-04', '23:21:34', '+0200',
            'CEST","CreatedSince":"5', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"44e19a16bde1","Repository":"debian","SharedSize":"N/A","Size":"55.3MB","Tag":"stretch-slim","UniqueSize":"N/A","VirtualSize":"55.27MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-08-06', '21:21:48', '+0200',
            'CEST","CreatedSince":"2', 'months',
            'ago","Digest":"\\u003cnone\\u003e","ID":"5182e96772bf","Repository":"centos","SharedSize":"N/A","Size":"200MB","Tag":"7","UniqueSize":"N/A","VirtualSize":"199.7MB"}'
        ]
    ],
    'image_labels': [
        [
            '[', '"sha256:485933207afd6e390c5e91f37b49b8610f483299de0bcff4b6fadca1cdb641b6",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0p5"}', ']'
        ],
        [
            '[', '"sha256:0983f5184ce73305dbba6b15bdb5ce90cb07790177690f4ce09e4a16b388842c",',
            '{"maintainer":"feedback@checkmk.com"}', ']'
        ],
        [
            '[', '"sha256:ed55e8b953366b628773629b98dba9adc07a9c1543efbb04c18f0052e26ee719",',
            '{"org.label-schema.build-date":"20180804","org.label-schema.license":"GPLv2","org.label-schema.name":"CentOS',
            'Base',
            'Image","org.label-schema.schema-version":"1.0","org.label-schema.vendor":"CentOS"}',
            ']'
        ],
        [
            '[', '"sha256:6c97da45403ae758af1cbc5a2480d5d5e8882c41a554eadc35e48769d641b15e",',
            '{"org.label-schema.build-date":"20180804","org.label-schema.license":"GPLv2","org.label-schema.name":"CentOS',
            'Base',
            'Image","org.label-schema.schema-version":"1.0","org.label-schema.vendor":"CentOS"}',
            ']'
        ],
        [
            '[', '"sha256:ed5d6b154e9754577224bc7f57e893f899664d4b0b336157063a714877024930",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.10.10"}', ']'
        ],
        [
            '[', '"sha256:df118e583614f41d5f190ced1a344ee3ccce2c36e91caf795d78e3c01d906701",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0p5"}', ']'
        ],
        [
            '[', '"sha256:4a77be28f8e54a4e6a8ecd8cfbd1963463d1e7ac719990206ced057af41e9957",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0p5"}', ']'
        ],
        [
            '[', '"sha256:f4bfbb70768f233f1adca8e9e7333695a263773c2663a97732519f3e0eed87b7",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0p3"}', ']'
        ],
        [
            '[', '"sha256:ff19a3911e0a1560a945c4d749cb47ffd1ca9397f506d195ae8d30a86f46807e",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.17"}', ']'
        ],
        [
            '[', '"sha256:c0582f734ad1bb8c9adaf014c6d0b90ec532bf137afcdb4afe304c0c581ed308",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:91152cc1c4bcd3aba6309d88b2c2a7e53f2e6209757f3fda180489f064994287",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:8ca14ae84dd9a788bcaddd196cbed346d6cd624fa1a63253728df769e26d2a21",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:44a5d6d152722adef8dada252863f178993d955b49caa8ea7b954d9ebc93b1c2",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0-2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:44a5d6d152722adef8dada252863f178993d955b49caa8ea7b954d9ebc93b1c2",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0-2018.09.14"}', ']'
        ],
        [
            '[', '"sha256:2e89feac75330553688011dfb2efc0f9c6e44b61a419d937ad826c8628007e10",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.13"}', ']'
        ],
        [
            '[', '"sha256:096300fde75dddfb273b343aa94957dffdbb4b57212debaddbd6f7714442df57",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0-2018.09.13"}', ']'
        ],
        [
            '[', '"sha256:8d463a5f7635ebd0c6f418236c571273083e1c5bc63711a2babc4048208f9aa3",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"1.5.0-2018.09.12"}', ']'
        ],
        [
            '[', '"sha256:a1f15f9a2b1640ac73437fc96b658b7c9907ab14127e1ec82cd93986874e3159",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.12"}', ']'
        ],
        [
            '[', '"sha256:ee5124a3adb5eb20012a7189ea34495da3e39ff8517c2c260954654d3edf1553",',
            '{"maintainer":"feedback@checkmk.com","org.opencontainers.image.description":"Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '&', 'Application',
            'Monitoring","org.opencontainers.image.source":"https://github.com/tribe29/checkmk","org.opencontainers.image.title":"Checkmk","org.opencontainers.image.url":"https://checkmk.com/","org.opencontainers.image.vendor":"tribe29',
             'GmbH","org.opencontainers.image.version":"2018.09.11"}', ']'
        ],
        [
            '[', '"sha256:6143303a8e14d19961946d8749b698e2d1a90262c62a11dee5a40367907afe88",',
            'null', ']'
        ],
        [
            '[', '"sha256:44e19a16bde1fd0f00b8cfb2b816e329ddee5c79869d140415f4445df4da485c",',
            'null', ']'
        ],
        [
            '[', '"sha256:5182e96772bf11f4b912658e265dfe0db8bd314475443b6434ea708784192892",',
            '{"org.label-schema.build-date":"20180804","org.label-schema.license":"GPLv2","org.label-schema.name":"CentOS',
            'Base',
            'Image","org.label-schema.schema-version":"1.0","org.label-schema.vendor":"CentOS"}',
            ']'
        ]
    ],
    'containers': [
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:12:19', '+0200',
            'CEST","ID":"802786d33cfb","Image":"010bad2c964b","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"boring_cori","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(100)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '16:12:02', '+0200',
            'CEST","ID":"11893c5d9694","Image":"559214f8c758","Labels":"org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk","LocalVolumes":"0","Mounts":"","Names":"affectionate_shannon","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '16:12:02', '+0200',
            'CEST","ID":"95796d6d26db","Image":"fcd54dfcb5b8","Labels":"org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH","LocalVolumes":"0","Mounts":"","Names":"distracted_heisenberg","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '16:12:01', '+0200',
            'CEST","ID":"58ea2160fe8f","Image":"3bd4e802a09f","Labels":"maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5","LocalVolumes":"0","Mounts":"","Names":"lucid_kowalevski","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '16:12:01', '+0200',
            'CEST","ID":"74ee5065acb2","Image":"a0529d041d12","Labels":"maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5","LocalVolumes":"0","Mounts":"","Names":"peaceful_joliot","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:11:24', '+0200',
            'CEST","ID":"7db7baa17fee","Image":"fd98c3cc9762","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"stoic_jennings","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:09:34', '+0200',
            'CEST","ID":"249ca074445f","Image":"010bad2c964b","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"infallible_goodall","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:07:29', '+0200',
            'CEST","ID":"63c0ad8e9eb7","Image":"0983f5184ce7","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"ecstatic_babbage","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(1)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:05:44', '+0200',
            'CEST","ID":"d91a2be75e8b","Image":"010bad2c964b","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"jovial_bardeen","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/usr/sbin/init\\"","CreatedAt":"2018-10-12', '11:13:24', '+0200',
            'CEST","ID":"f1641e401237","Image":"local/c7-systemd-httpd","Labels":"org.label-schema.schema-version=1.0,org.label-schema.vendor=CentOS,org.label-schema.build-date=20180804,org.label-schema.license=GPLv2,org.label-schema.name=CentOS',
            'Base',
            'Image","LocalVolumes":"0","Mounts":"/sys/fs/cgroup","Names":"sad_stonebraker","Networks":"bridge","Ports":"","RunningFor":"4',
            'days', 'ago","Size":"0B","Status":"Exited', '(137)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/usr/sbin/init\\"","CreatedAt":"2018-10-12', '11:13:18', '+0200',
            'CEST","ID":"7d32581dd10f","Image":"local/c7-systemd-httpd","Labels":"org.label-schema.build-date=20180804,org.label-schema.license=GPLv2,org.label-schema.name=CentOS',
            'Base',
            'Image,org.label-schema.schema-version=1.0,org.label-schema.vendor=CentOS","LocalVolumes":"0","Mounts":"/sys/fs/cgroup","Names":"sad_austin","Networks":"bridge","Ports":"","RunningFor":"4',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '09:17:54', '+0200',
            'CEST","ID":"fdd04795069e","Image":"checkmk/check-mk-raw:1.5.0p5","Labels":"maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5","LocalVolumes":"1","Mounts":"/etc/localtime,10b7c962177bf2\xe2\x80\xa6","Names":"monitoringx","Networks":"bridge","Ports":"6557/tcp,',
            '0.0.0.0:8080-\\u003e5000/tcp","RunningFor":"4', 'days',
            'ago","Size":"0B","Status":"Up', '6', 'hours', '(healthy)"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:40:21', '+0200',
            'CEST","ID":"b17185d5dcc5","Image":"94f49a7afedb","Labels":"org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk","LocalVolumes":"0","Mounts":"","Names":"friendly_banach","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:40:20', '+0200',
            'CEST","ID":"73237ecc5183","Image":"d27276979703","Labels":"org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk","LocalVolumes":"0","Mounts":"","Names":"festive_stallman","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:40:20', '+0200',
            'CEST","ID":"0d7e34ebb911","Image":"03d98e475cd6","Labels":"org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH","LocalVolumes":"0","Mounts":"","Names":"youthful_pare","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:40:20', '+0200',
            'CEST","ID":"580a7b4bd20a","Image":"3e0dd44b22e4","Labels":"org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/","LocalVolumes":"0","Mounts":"","Names":"reverent_proskuriakova","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10', '08:39:29', '+0200',
            'CEST","ID":"4a6806b168b1","Image":"089108b69108","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"festive_fermi","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '6', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10', '08:37:43', '+0200',
            'CEST","ID":"93e0c88a69fa","Image":"b16a30c66821","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"objective_darwin","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '6', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:37:26', '+0200',
            'CEST","ID":"6fe73b950209","Image":"d4c95e27986c","Labels":"org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH","LocalVolumes":"0","Mounts":"","Names":"admiring_haibt","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:37:26', '+0200',
            'CEST","ID":"bfdb64ccf0ba","Image":"21b2f3d5e6c0","Labels":"maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5","LocalVolumes":"0","Mounts":"","Names":"lucid_bohr","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:37:25', '+0200',
            'CEST","ID":"24772268cc09","Image":"6e66f5473958","Labels":"org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk","LocalVolumes":"0","Mounts":"","Names":"zen_bartik","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:37:25', '+0200',
            'CEST","ID":"8f8ded35fc90","Image":"6bccd8c3ed71","Labels":"org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring","LocalVolumes":"0","Mounts":"","Names":"keen_cori","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10', '08:36:45', '+0200',
            'CEST","ID":"a073bb9adfbe","Image":"7aa4b82c92ae","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"jovial_archimedes","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '6', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10', '08:34:58', '+0200',
            'CEST","ID":"4d4d9f3be74b","Image":"b16a30c66821","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"pensive_spence","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '6', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:58', '+0200',
            'CEST","ID":"df44340ed121","Image":"1b013e043efa","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"unruffled_hopper","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:58', '+0200',
            'CEST","ID":"860d8dfff4f6","Image":"7e7f944ba518","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"dazzling_meninsky","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:57', '+0200',
            'CEST","ID":"a17f21f95383","Image":"a2a187fcaa76","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"serene_poincare","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:57', '+0200',
            'CEST","ID":"6cae82f879ff","Image":"1d9b21b9e019","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"elated_poitras","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:57', '+0200',
            'CEST","ID":"aad80d524200","Image":"e002e37aec84","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"competent_keller","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:56', '+0200',
            'CEST","ID":"d1c70f4690b5","Image":"0b5da1249a04","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"trusting_panini","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:56', '+0200',
            'CEST","ID":"9b08cf26da8c","Image":"164429e47a3f","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"pensive_swartz","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:56', '+0200',
            'CEST","ID":"c04099ed3f18","Image":"d1a41c564864","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"dreamy_thompson","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:56', '+0200',
            'CEST","ID":"cdc7e1e4a24e","Image":"999fc035fc76","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"lucid_brown","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:55', '+0200',
            'CEST","ID":"10d6b884f348","Image":"a0a951b126eb","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"wizardly_ritchie","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:55', '+0200',
            'CEST","ID":"d37198a74c08","Image":"caac4aa6ac57","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"distracted_mccarthy","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:55', '+0200',
            'CEST","ID":"55632dca94c8","Image":"1919d446eafa","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"stoic_perlman","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/bash\\"","CreatedAt":"2018-09-27', '19:06:07', '+0200',
            'CEST","ID":"85a41e54b0cc","Image":"centos:7","Labels":"org.label-schema.build-date=20180804,org.label-schema.license=GPLv2,org.label-schema.name=CentOS',
            'Base',
            'Image,org.label-schema.schema-version=1.0,org.label-schema.vendor=CentOS","LocalVolumes":"0","Mounts":"","Names":"vigorous_pare","Networks":"bridge","Ports":"","RunningFor":"2',
            'weeks', 'ago","Size":"0B","Status":"Exited', '(137)', '2', 'weeks', 'ago"}'
        ]
    ]
}

EXPECTED_CONTAINERS2 = {
    u'0d7e34ebb911': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:40:20 +0200 CEST',
        u'Id': u'0d7e34ebb911',
        u'Image': u'03d98e475cd6',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.10.10'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'youthful_pare',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'10d6b884f348': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:55 +0200 CEST',
        u'Id': u'10d6b884f348',
        u'Image': u'a0a951b126eb',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'wizardly_ritchie',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'11893c5d9694': {
        u'Command': u'"/docker-entrypoint.\u2026"',
        u'Created': u'2018-10-12 16:12:02 +0200 CEST',
        u'Id': u'11893c5d9694',
        u'Image': u'559214f8c758',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'affectionate_shannon',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'3 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'24772268cc09': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:37:25 +0200 CEST',
        u'Id': u'24772268cc09',
        u'Image': u'6e66f5473958',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'zen_bartik',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'249ca074445f': {
        u'Command': u'"/bin/sh -c \'set -e \u2026"',
        u'Created': u'2018-10-12 16:09:34 +0200 CEST',
        u'Id': u'249ca074445f',
        u'Image': u'010bad2c964b',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'infallible_goodall',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'3 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (0) 3 days ago',
    },
    u'4a6806b168b1': {
        u'Command': u'"/bin/sh -c \'set -e \u2026"',
        u'Created': u'2018-10-10 08:39:29 +0200 CEST',
        u'Id': u'4a6806b168b1',
        u'Image': u'089108b69108',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'festive_fermi',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (0) 6 days ago',
    },
    u'4d4d9f3be74b': {
        u'Command': u'"/bin/sh -c \'set -e \u2026"',
        u'Created': u'2018-10-10 08:34:58 +0200 CEST',
        u'Id': u'4d4d9f3be74b',
        u'Image': u'b16a30c66821',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'pensive_spence',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (0) 6 days ago',
    },
    u'55632dca94c8': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:55 +0200 CEST',
        u'Id': u'55632dca94c8',
        u'Image': u'1919d446eafa',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'stoic_perlman',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'580a7b4bd20a': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:40:20 +0200 CEST',
        u'Id': u'580a7b4bd20a',
        u'Image': u'3e0dd44b22e4',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.10.10'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'reverent_proskuriakova',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'58ea2160fe8f': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-12 16:12:01 +0200 CEST',
        u'Id': u'58ea2160fe8f',
        u'Image': u'3bd4e802a09f',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'lucid_kowalevski',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'3 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'63c0ad8e9eb7': {
        u'Command': u'"/bin/sh -c \'set -e \u2026"',
        u'Created': u'2018-10-12 16:07:29 +0200 CEST',
        u'Id': u'63c0ad8e9eb7',
        u'Image': u'0983f5184ce7',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'ecstatic_babbage',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'3 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (1) 3 days ago',
    },
    u'6cae82f879ff': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:57 +0200 CEST',
        u'Id': u'6cae82f879ff',
        u'Image': u'1d9b21b9e019',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'elated_poitras',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'6fe73b950209': {
        u'Command': u'"/docker-entrypoint.\u2026"',
        u'Created': u'2018-10-10 08:37:26 +0200 CEST',
        u'Id': u'6fe73b950209',
        u'Image': u'd4c95e27986c',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'admiring_haibt',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'73237ecc5183': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:40:20 +0200 CEST',
        u'Id': u'73237ecc5183',
        u'Image': u'd27276979703',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.10.10'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'festive_stallman',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'74ee5065acb2': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-12 16:12:01 +0200 CEST',
        u'Id': u'74ee5065acb2',
        u'Image': u'a0529d041d12',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'peaceful_joliot',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'3 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'7d32581dd10f': {
        u'Command': u'"/usr/sbin/init"',
        u'Created': u'2018-10-12 11:13:18 +0200 CEST',
        u'Id': u'7d32581dd10f',
        u'Image': u'local/c7-systemd-httpd',
        u'Labels': {
            u'org.label-schema.build-date': u'20180804',
            u'org.label-schema.license': u'GPLv2',
            u'org.label-schema.name': u'CentOS Base Image',
            u'org.label-schema.schema-version': u'1.0',
            u'org.label-schema.vendor': u'CentOS'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'/sys/fs/cgroup',
        u'Name': u'sad_austin',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'4 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'7db7baa17fee': {
        u'Command': u'"/bin/sh -c \'set -e \u2026"',
        u'Created': u'2018-10-12 16:11:24 +0200 CEST',
        u'Id': u'7db7baa17fee',
        u'Image': u'fd98c3cc9762',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'stoic_jennings',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'3 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (0) 3 days ago',
    },
    u'802786d33cfb': {
        u'Command': u'"/bin/sh -c \'set -e \u2026"',
        u'Created': u'2018-10-12 16:12:19 +0200 CEST',
        u'Id': u'802786d33cfb',
        u'Image': u'010bad2c964b',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'boring_cori',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'3 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (100) 3 days ago',
    },
    u'85a41e54b0cc': {
        u'Command': u'"/bin/bash"',
        u'Created': u'2018-09-27 19:06:07 +0200 CEST',
        u'Id': u'85a41e54b0cc',
        u'Image': u'centos:7',
        u'Labels': {
            u'org.label-schema.build-date': u'20180804',
            u'org.label-schema.license': u'GPLv2',
            u'org.label-schema.name': u'CentOS Base Image',
            u'org.label-schema.schema-version': u'1.0',
            u'org.label-schema.vendor': u'CentOS'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'vigorous_pare',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'2 weeks ago',
        u'Size': u'0B',
        u'Status': u'Exited (137) 2 weeks ago',
    },
    u'860d8dfff4f6': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:58 +0200 CEST',
        u'Id': u'860d8dfff4f6',
        u'Image': u'7e7f944ba518',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'dazzling_meninsky',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'8f8ded35fc90': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:37:25 +0200 CEST',
        u'Id': u'8f8ded35fc90',
        u'Image': u'6bccd8c3ed71',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'keen_cori',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'93e0c88a69fa': {
        u'Command': u'"/bin/sh -c \'set -e \u2026"',
        u'Created': u'2018-10-10 08:37:43 +0200 CEST',
        u'Id': u'93e0c88a69fa',
        u'Image': u'b16a30c66821',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'objective_darwin',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (0) 6 days ago',
    },
    u'95796d6d26db': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-12 16:12:02 +0200 CEST',
        u'Id': u'95796d6d26db',
        u'Image': u'fcd54dfcb5b8',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'distracted_heisenberg',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'3 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'9b08cf26da8c': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:56 +0200 CEST',
        u'Id': u'9b08cf26da8c',
        u'Image': u'164429e47a3f',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'pensive_swartz',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'a073bb9adfbe': {
        u'Command': u'"/bin/sh -c \'set -e \u2026"',
        u'Created': u'2018-10-10 08:36:45 +0200 CEST',
        u'Id': u'a073bb9adfbe',
        u'Image': u'7aa4b82c92ae',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'jovial_archimedes',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (0) 6 days ago',
    },
    u'a17f21f95383': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:57 +0200 CEST',
        u'Id': u'a17f21f95383',
        u'Image': u'a2a187fcaa76',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'serene_poincare',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'aad80d524200': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:57 +0200 CEST',
        u'Id': u'aad80d524200',
        u'Image': u'e002e37aec84',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'competent_keller',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'b17185d5dcc5': {
        u'Command': u'"/docker-entrypoint.\u2026"',
        u'Created': u'2018-10-10 08:40:21 +0200 CEST',
        u'Id': u'b17185d5dcc5',
        u'Image': u'94f49a7afedb',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.10.10'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'friendly_banach',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'bfdb64ccf0ba': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:37:26 +0200 CEST',
        u'Id': u'bfdb64ccf0ba',
        u'Image': u'21b2f3d5e6c0',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'lucid_bohr',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'c04099ed3f18': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:56 +0200 CEST',
        u'Id': u'c04099ed3f18',
        u'Image': u'd1a41c564864',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'dreamy_thompson',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'cdc7e1e4a24e': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:56 +0200 CEST',
        u'Id': u'cdc7e1e4a24e',
        u'Image': u'999fc035fc76',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'lucid_brown',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'd1c70f4690b5': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:56 +0200 CEST',
        u'Id': u'd1c70f4690b5',
        u'Image': u'0b5da1249a04',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'trusting_panini',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'd37198a74c08': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:55 +0200 CEST',
        u'Id': u'd37198a74c08',
        u'Image': u'caac4aa6ac57',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'distracted_mccarthy',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'd91a2be75e8b': {
        u'Command': u'"/bin/sh -c \'set -e \u2026"',
        u'Created': u'2018-10-12 16:05:44 +0200 CEST',
        u'Id': u'd91a2be75e8b',
        u'Image': u'010bad2c964b',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'jovial_bardeen',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'3 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (0) 3 days ago',
    },
    u'df44340ed121': {
        u'Command': u'"/bin/sh -c \'#(nop) \u2026"',
        u'Created': u'2018-10-10 08:34:58 +0200 CEST',
        u'Id': u'df44340ed121',
        u'Image': u'1b013e043efa',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'',
        u'Name': u'unruffled_hopper',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'6 days ago',
        u'Size': u'0B',
        u'Status': u'Created',
    },
    u'f1641e401237': {
        u'Command': u'"/usr/sbin/init"',
        u'Created': u'2018-10-12 11:13:24 +0200 CEST',
        u'Id': u'f1641e401237',
        u'Image': u'local/c7-systemd-httpd',
        u'Labels': {
            u'org.label-schema.build-date': u'20180804',
            u'org.label-schema.license': u'GPLv2',
            u'org.label-schema.name': u'CentOS Base Image',
            u'org.label-schema.schema-version': u'1.0',
            u'org.label-schema.vendor': u'CentOS'
        },
        u'LocalVolumes': u'0',
        u'Mounts': u'/sys/fs/cgroup',
        u'Name': u'sad_stonebraker',
        u'Networks': u'bridge',
        u'Ports': u'',
        u'RunningFor': u'4 days ago',
        u'Size': u'0B',
        u'Status': u'Exited (137) 3 days ago',
    },
    u'fdd04795069e': {
        u'Command': u'"/docker-entrypoint.\u2026"',
        u'Created': u'2018-10-12 09:17:54 +0200 CEST',
        u'Id': u'fdd04795069e',
        u'Image': u'checkmk/check-mk-raw:1.5.0p5',
        u'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        u'LocalVolumes': u'1',
        u'Mounts': u'/etc/localtime,10b7c962177bf2\u2026',
        u'Name': u'monitoringx',
        u'Networks': u'bridge',
        u'Ports': u'6557/tcp, 0.0.0.0:8080->5000/tcp',
        u'RunningFor': u'4 days ago',
        u'Size': u'0B',
        u'Status': u'Up 6 hours (healthy)',
    }
}

EXPECTED_IMAGES2 = {
    u'096300fde75d': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-13 08:15:30 +0200 CEST',
        u'CreatedSince': u'4 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'096300fde75d',
        u'RepoTags': ['checkmk/check-mk-enterprise:1.5.0-2018.09.13'],
        u'SharedSize': u'N/A',
        u'Size': u'818MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 818000000,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0-2018.09.13'
        },
        'amount_containers': 0
    },
    u'0983f5184ce7': {
        u'Containers': u'N/A',
        u'Created': u'2018-10-12 16:07:29 +0200 CEST',
        u'CreatedSince': u'3 days ago',
        u'Digest': u'<none>',
        u'Id': u'0983f5184ce7',
        u'SharedSize': u'N/A',
        u'Size': u'312MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 312400000,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        'amount_containers': 1
    },
    u'2e89feac7533': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-13 08:27:42 +0200 CEST',
        u'CreatedSince': u'4 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'2e89feac7533',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-2018.09.13:latest'],
        u'SharedSize': u'N/A',
        u'Size': u'831MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 831400000,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.09.13'
        },
        'amount_containers': 0
    },
    u'44a5d6d15272': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-14 12:45:50 +0200 CEST',
        u'CreatedSince': u'4 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'44a5d6d15272',
        u'RepoTags': ['checkmk/check-mk-enterprise:1.5.0-daily'],
        u'SharedSize': u'N/A',
        u'Size': u'818MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 818000000,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0-2018.09.14'
        },
        'amount_containers': 0
    },
    u'44e19a16bde1': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-04 23:21:34 +0200 CEST',
        u'CreatedSince': u'5 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'44e19a16bde1',
        u'RepoTags': ['debian:stretch-slim'],
        u'SharedSize': u'N/A',
        u'Size': u'55.3MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 55270000,
        'amount_containers': 0
    },
    u'485933207afd': {
        u'Containers': u'N/A',
        u'Created': u'2018-10-12 16:12:03 +0200 CEST',
        u'CreatedSince': u'3 days ago',
        u'Digest': u'<none>',
        u'Id': u'485933207afd',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-1.5.0p5:latest'],
        u'SharedSize': u'N/A',
        u'Size': u'818MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 817600000,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        'amount_containers': 0
    },
    u'4a77be28f8e5': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-28 23:54:16 +0200 CEST',
        u'CreatedSince': u'2 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'4a77be28f8e5',
        u'RepoTags': ['checkmk/check-mk-raw:1.5.0p5'],
        u'SharedSize': u'N/A',
        u'Size': u'752MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 751900000,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        'amount_containers': 1
    },
    u'5182e96772bf': {
        u'Containers': u'N/A',
        u'Created': u'2018-08-06 21:21:48 +0200 CEST',
        u'CreatedSince': u'2 months ago',
        u'Digest': u'<none>',
        u'Id': u'5182e96772bf',
        u'RepoTags': ['centos:7'],
        u'SharedSize': u'N/A',
        u'Size': u'200MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 199700000,
        'Labels': {
            u'org.label-schema.build-date': u'20180804',
            u'org.label-schema.license': u'GPLv2',
            u'org.label-schema.name': u'CentOS Base Image',
            u'org.label-schema.schema-version': u'1.0',
            u'org.label-schema.vendor': u'CentOS'
        },
        'amount_containers': 1
    },
    u'6143303a8e14': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-10 17:36:25 +0200 CEST',
        u'CreatedSince': u'5 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'6143303a8e14',
        u'RepoTags': ['hadolint/hadolint:latest'],
        u'SharedSize': u'N/A',
        u'Size': u'3.64MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 3645000,
        'amount_containers': 0
    },
    u'6c97da45403a': {
        u'Containers': u'N/A',
        u'Created': u'2018-10-12 11:12:15 +0200 CEST',
        u'CreatedSince': u'4 days ago',
        u'Digest': u'<none>',
        u'Id': u'6c97da45403a',
        u'RepoTags': ['local/c7-systemd:latest'],
        u'SharedSize': u'N/A',
        u'Size': u'200MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 199700000,
        'Labels': {
            u'org.label-schema.build-date': u'20180804',
            u'org.label-schema.license': u'GPLv2',
            u'org.label-schema.name': u'CentOS Base Image',
            u'org.label-schema.schema-version': u'1.0',
            u'org.label-schema.vendor': u'CentOS'
        },
        'amount_containers': 0
    },
    u'8ca14ae84dd9': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-14 13:08:54 +0200 CEST',
        u'CreatedSince': u'4 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'8ca14ae84dd9',
        u'RepoTags': ['checkmk/check-mk-enterprise:daily'],
        u'SharedSize': u'N/A',
        u'Size': u'972MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 972300000,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.09.14'
        },
        'amount_containers': 0
    },
    u'8d463a5f7635': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-12 21:15:47 +0200 CEST',
        u'CreatedSince': u'4 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'8d463a5f7635',
        u'RepoTags': ['checkmk/check-mk-enterprise:1.5.0-2018.09.12'],
        u'SharedSize': u'N/A',
        u'Size': u'815MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 814900000,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0-2018.09.12'
        },
        'amount_containers': 0
    },
    u'91152cc1c4bc': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-14 14:47:41 +0200 CEST',
        u'CreatedSince': u'4 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'91152cc1c4bc',
        u'RepoTags': ['docker-tests/check-mk-enterprise-master-2018.09.14:latest'],
        u'SharedSize': u'N/A',
        u'Size': u'831MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 831400000,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.09.14'
        },
        'amount_containers': 0
    },
}

SUBSECTIONS3 = {
    'images': [
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '16:12:03', '+0200',
            'CEST","CreatedSince":"3', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"485933207afd","Repository":"docker-tests/check-mk-enterprise-master-1.5.0p5","SharedSize":"N/A","Size":"818MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"817.6MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '16:07:29', '+0200',
            'CEST","CreatedSince":"3', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"0983f5184ce7","Repository":"\\u003cnone\\u003e","SharedSize":"N/A","Size":"312MB","Tag":"\\u003cnone\\u003e","UniqueSize":"N/A","VirtualSize":"312.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '11:13:11', '+0200',
            'CEST","CreatedSince":"4', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"ed55e8b95336","Repository":"local/c7-systemd-httpd","SharedSize":"N/A","Size":"254MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"254.2MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-12', '11:12:15', '+0200',
            'CEST","CreatedSince":"4', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"6c97da45403a","Repository":"local/c7-systemd","SharedSize":"N/A","Size":"200MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"199.7MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-10', '08:40:21', '+0200',
            'CEST","CreatedSince":"6', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"ed5d6b154e97","Repository":"docker-tests/check-mk-enterprise-master-2018.10.10","SharedSize":"N/A","Size":"844MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"844.3MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-10-10', '08:37:26', '+0200',
            'CEST","CreatedSince":"6', 'days',
            'ago","Digest":"\\u003cnone\\u003e","ID":"df118e583614","Repository":"\\u003cnone\\u003e","SharedSize":"N/A","Size":"818MB","Tag":"\\u003cnone\\u003e","UniqueSize":"N/A","VirtualSize":"817.6MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-28', '23:54:16', '+0200',
            'CEST","CreatedSince":"2', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"4a77be28f8e5","Repository":"checkmk/check-mk-raw","SharedSize":"N/A","Size":"752MB","Tag":"1.5.0p5","UniqueSize":"N/A","VirtualSize":"751.9MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-17', '09:47:56', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"f4bfbb70768f","Repository":"docker-tests/check-mk-enterprise-master-1.5.0p3","SharedSize":"N/A","Size":"817MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"817.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-17', '09:45:08', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"ff19a3911e0a","Repository":"docker-tests/check-mk-enterprise-master-2018.09.17","SharedSize":"N/A","Size":"831MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '16:52:00', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"c0582f734ad1","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"831MB","Tag":"2018.09.14","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '14:47:41', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"91152cc1c4bc","Repository":"docker-tests/check-mk-enterprise-master-2018.09.14","SharedSize":"N/A","Size":"831MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '13:08:54', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"8ca14ae84dd9","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"972MB","Tag":"daily","UniqueSize":"N/A","VirtualSize":"972.3MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '12:45:50', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"44a5d6d15272","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"818MB","Tag":"1.5.0-2018.09.14","UniqueSize":"N/A","VirtualSize":"818MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-14', '12:45:50', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"44a5d6d15272","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"818MB","Tag":"1.5.0-daily","UniqueSize":"N/A","VirtualSize":"818MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-13', '08:27:42', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"2e89feac7533","Repository":"docker-tests/check-mk-enterprise-master-2018.09.13","SharedSize":"N/A","Size":"831MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"831.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-13', '08:15:30', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"096300fde75d","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"818MB","Tag":"1.5.0-2018.09.13","UniqueSize":"N/A","VirtualSize":"818MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-12', '21:15:47', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"8d463a5f7635","Repository":"checkmk/check-mk-enterprise","SharedSize":"N/A","Size":"815MB","Tag":"1.5.0-2018.09.12","UniqueSize":"N/A","VirtualSize":"814.9MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-12', '19:49:54', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"a1f15f9a2b16","Repository":"docker-tests/check-mk-enterprise-master-2018.09.12","SharedSize":"N/A","Size":"828MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"828.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-12', '09:33:22', '+0200',
            'CEST","CreatedSince":"4', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"ee5124a3adb5","Repository":"docker-tests/check-mk-enterprise-master-2018.09.11","SharedSize":"N/A","Size":"828MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"828.4MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-10', '17:36:25', '+0200',
            'CEST","CreatedSince":"5', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"6143303a8e14","Repository":"hadolint/hadolint","SharedSize":"N/A","Size":"3.64MB","Tag":"latest","UniqueSize":"N/A","VirtualSize":"3.645MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-09-04', '23:21:34', '+0200',
            'CEST","CreatedSince":"5', 'weeks',
            'ago","Digest":"\\u003cnone\\u003e","ID":"44e19a16bde1","Repository":"debian","SharedSize":"N/A","Size":"55.3MB","Tag":"stretch-slim","UniqueSize":"N/A","VirtualSize":"55.27MB"}'
        ],
        [
            '{"Containers":"N/A","CreatedAt":"2018-08-06', '21:21:48', '+0200',
            'CEST","CreatedSince":"2', 'months',
            'ago","Digest":"\\u003cnone\\u003e","ID":"5182e96772bf","Repository":"centos","SharedSize":"N/A","Size":"200MB","Tag":"7","UniqueSize":"N/A","VirtualSize":"199.7MB"}'
        ]
    ],
    'image_inspect': [
        ['['], ['{'],
        ['"Id":', '"sha256:485933207afd6e390c5e91f37b49b8610f483299de0bcff4b6fadca1cdb641b6",'],
        ['"RepoTags":', '['], ['"docker-tests/check-mk-enterprise-master-1.5.0p5:latest"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:559214f8c75811dd06bbb9de1c7b913c6897ff888e01f7b4706e3a48d6e58fa7",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-10-12T14:12:03.009245184Z",'],
        ['"Container":', '"11893c5d9694c63fb20fd2f0954cb050d0d74dc1acad836bc6abf0523eca761d",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"11893c5d9694",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:559214f8c75811dd06bbb9de1c7b913c6897ff888e01f7b4706e3a48d6e58fa7",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0p5"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:559214f8c75811dd06bbb9de1c7b913c6897ff888e01f7b4706e3a48d6e58fa7",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0p5"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '817562729,'],
        ['"VirtualSize":', '817562729,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/36717fcfd9d46ebfc071e8cb87888fd302a79712893543d2b4c4bfdc65e999be/diff:/var/lib/docker/overlay2/4819e3e13f5c851d3b10d6173290653db9975b5f8dcf46ccb8357903cf528d4c/diff:/var/lib/docker/overlay2/1bf00a1119b20c5c590dc605f4e498b66773ea805ff515af0800b75700bf5eaf/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/981d9bc20f6e3bd84789ce166c8d22b6b7fbbabfeb658b646bffd65a7db521f3/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/981d9bc20f6e3bd84789ce166c8d22b6b7fbbabfeb658b646bffd65a7db521f3/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/981d9bc20f6e3bd84789ce166c8d22b6b7fbbabfeb658b646bffd65a7db521f3/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:334729b85709a3cff4202819f482744663072fb358e6628e57277f75cdd1fbe8",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:4d7354b9323b2578c01385f10426db1fc2c34bafc6f29d1a0f4ed1f8e3f099ab",'],
        ['"sha256:f38c27b130eff9fa2fdc02c2563d26395763842b20be6153225232379a35d098"'], [']'],
        ['},'], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-10-12T16:12:03.074548501+02:00"'],
        ['}'], ['},'], ['{'],
        ['"Id":', '"sha256:0983f5184ce73305dbba6b15bdb5ce90cb07790177690f4ce09e4a16b388842c",'],
        ['"RepoTags":', '[],'], ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:6cd8be12f4ea663ccba3050c4e49bd24ab2133bcd6582b98d11e1d3075cd8a6e",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-10-12T14:07:29.732808446Z",'],
        ['"Container":', '"",'], ['"ContainerConfig":', '{'], ['"Hostname":', '"",'],
        ['"Domainname":', '"",'], ['"User":', '"",'], ['"AttachStdin":', 'false,'],
        ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'], ['"Tty":', 'false,'],
        ['"OpenStdin":', 'false,'], ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', '['], ['"/bin/sh",'], ['"-c",'],
        [
            '"#(nop)', 'COPY',
            'file:ef4b1a9d6d7969ffea8d085c3d8800354ccb4ed9d757de4c3067f86e4fe564da', 'in', '/', '"'
        ], ['],'], ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:6cd8be12f4ea663ccba3050c4e49bd24ab2133bcd6582b98d11e1d3075cd8a6e",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', 'null,'],
        ['"OnBuild":', 'null,'], ['"Labels":', '{'], ['"maintainer":', '"feedback@checkmk.com"'],
        ['}'], ['},'], ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'],
        ['"Config":', '{'], ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', '['], ['"bash"'], ['],'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:6cd8be12f4ea663ccba3050c4e49bd24ab2133bcd6582b98d11e1d3075cd8a6e",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', 'null,'],
        ['"OnBuild":', 'null,'], ['"Labels":', '{'], ['"maintainer":', '"feedback@checkmk.com"'],
        ['}'], ['},'], ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'],
        ['"Size":', '312404556,'], ['"VirtualSize":', '312404556,'], ['"GraphDriver":', '{'],
        ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/36bd42fec61aa7ffb5f6ebf40b07d846fd9e3e2177583bc358f8d20cdbdd19a5/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/911f88ea587f18328cc711fb1e718dffb52e73509bb38e607cd7a66dba764903/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/911f88ea587f18328cc711fb1e718dffb52e73509bb38e607cd7a66dba764903/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/911f88ea587f18328cc711fb1e718dffb52e73509bb38e607cd7a66dba764903/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:ec0ac2b755908c6ce73337fbcf4328a543cff2fe1c6a20fbffbd3568b807d163",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d"'], [']'],
        ['},'], ['"Metadata":', '{'], ['"LastTagTime":', '"0001-01-01T00:00:00Z"'], ['}'], ['},'],
        ['{'],
        ['"Id":', '"sha256:ed55e8b953366b628773629b98dba9adc07a9c1543efbb04c18f0052e26ee719",'],
        ['"RepoTags":',
         '['], ['"local/c7-systemd-httpd:latest"'], ['],'], ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:2d30c3161955bd57fce74f2d9337dd8b013903bb60afefb57b459aa2749a48ae",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-10-12T09:13:11.560711878Z",'],
        ['"Container":', '"20fe7f741401c07d1bc9859c797ba480b4e471bb22374b57859d023ba05ec7e1",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"20fe7f741401",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"80/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"container=docker"'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"CMD', '[\\"/usr/sbin/init\\"]"'], ['],'], ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:2d30c3161955bd57fce74f2d9337dd8b013903bb60afefb57b459aa2749a48ae",'],
        ['"Volumes":', '{'], ['"/sys/fs/cgroup":', '{}'], ['},'], ['"WorkingDir":', '"",'],
        ['"Entrypoint":', 'null,'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"org.label-schema.build-date":', '"20180804",'],
        ['"org.label-schema.license":', '"GPLv2",'],
        ['"org.label-schema.name":', '"CentOS', 'Base', 'Image",'],
        ['"org.label-schema.schema-version":',
         '"1.0",'], ['"org.label-schema.vendor":', '"CentOS"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"80/tcp":', '{}'], ['},'], ['"Tty":', 'false,'],
        ['"OpenStdin":', 'false,'], ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"container=docker"'], ['],'], ['"Cmd":', '['], ['"/usr/sbin/init"'], ['],'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:2d30c3161955bd57fce74f2d9337dd8b013903bb60afefb57b459aa2749a48ae",'],
        ['"Volumes":', '{'], ['"/sys/fs/cgroup":', '{}'], ['},'], ['"WorkingDir":', '"",'],
        ['"Entrypoint":', 'null,'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"org.label-schema.build-date":', '"20180804",'],
        ['"org.label-schema.license":', '"GPLv2",'],
        ['"org.label-schema.name":', '"CentOS', 'Base', 'Image",'],
        ['"org.label-schema.schema-version":',
         '"1.0",'], ['"org.label-schema.vendor":', '"CentOS"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '254189650,'],
        ['"VirtualSize":', '254189650,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/a848609050aa570fe654987fbb06b66a73bf8795b0e1f71df14ac4327bda00a6/diff:/var/lib/docker/overlay2/1727960010f698e148cb98e9cf81d09ea52537deba2f7be30bc80e940f54562e/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/81851613afd1c6982b028041264d62c9ffcb7b1087f5473bbb20e4b54e4c49bc/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/81851613afd1c6982b028041264d62c9ffcb7b1087f5473bbb20e4b54e4c49bc/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/81851613afd1c6982b028041264d62c9ffcb7b1087f5473bbb20e4b54e4c49bc/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:1d31b5806ba40b5f67bde96f18a181668348934a44c9253b420d5f04cfb4e37a",'],
        ['"sha256:70d085f0b674c875cbe5a6c2357141fde504cb56986e25b137a7b2f219cea3f2",'],
        ['"sha256:afabd31398f3f1c2f631a88d0735d3b2bf7affbfe7231224fbc1ba68798bca30"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-10-12T11:13:11.647482428+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:6c97da45403ae758af1cbc5a2480d5d5e8882c41a554eadc35e48769d641b15e",'],
        ['"RepoTags":', '['], ['"local/c7-systemd:latest"'], ['],'], ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:5793c0f1e43ec81b40acb513e6cd56e332b2a552e1f9293d0bd0884c3847b8b1",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-10-12T09:12:15.613593451Z",'],
        ['"Container":', '"fe6503c8f3fb2e86dee85e2b0e8318075b1b359513f999d74731310908d4952c",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"fe6503c8f3fb",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"container=docker"'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"CMD', '[\\"/usr/sbin/init\\"]"'], ['],'], ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:5793c0f1e43ec81b40acb513e6cd56e332b2a552e1f9293d0bd0884c3847b8b1",'],
        ['"Volumes":', '{'], ['"/sys/fs/cgroup":', '{}'], ['},'], ['"WorkingDir":', '"",'],
        ['"Entrypoint":', 'null,'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"org.label-schema.build-date":', '"20180804",'],
        ['"org.label-schema.license":', '"GPLv2",'],
        ['"org.label-schema.name":', '"CentOS', 'Base', 'Image",'],
        ['"org.label-schema.schema-version":',
         '"1.0",'], ['"org.label-schema.vendor":', '"CentOS"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"container=docker"'], ['],'], ['"Cmd":', '['], ['"/usr/sbin/init"'], ['],'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:5793c0f1e43ec81b40acb513e6cd56e332b2a552e1f9293d0bd0884c3847b8b1",'],
        ['"Volumes":', '{'], ['"/sys/fs/cgroup":', '{}'], ['},'], ['"WorkingDir":', '"",'],
        ['"Entrypoint":', 'null,'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"org.label-schema.build-date":', '"20180804",'],
        ['"org.label-schema.license":', '"GPLv2",'],
        ['"org.label-schema.name":', '"CentOS', 'Base', 'Image",'],
        ['"org.label-schema.schema-version":',
         '"1.0",'], ['"org.label-schema.vendor":', '"CentOS"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '199723824,'],
        ['"VirtualSize":', '199723824,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/1727960010f698e148cb98e9cf81d09ea52537deba2f7be30bc80e940f54562e/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/a848609050aa570fe654987fbb06b66a73bf8795b0e1f71df14ac4327bda00a6/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/a848609050aa570fe654987fbb06b66a73bf8795b0e1f71df14ac4327bda00a6/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/a848609050aa570fe654987fbb06b66a73bf8795b0e1f71df14ac4327bda00a6/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:1d31b5806ba40b5f67bde96f18a181668348934a44c9253b420d5f04cfb4e37a",'],
        ['"sha256:70d085f0b674c875cbe5a6c2357141fde504cb56986e25b137a7b2f219cea3f2"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-10-12T11:12:15.709364573+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:ed5d6b154e9754577224bc7f57e893f899664d4b0b336157063a714877024930",'],
        ['"RepoTags":',
         '['], ['"docker-tests/check-mk-enterprise-master-2018.10.10:latest"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:94f49a7afedbb29d237891f6c4039db2e73960d3a02499a66b4158e36e18119f",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-10-10T06:40:21.695138758Z",'],
        ['"Container":', '"b17185d5dcc558857e216a449561a32dbef7b86d277d62995f3f4fc3e2f47832",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"b17185d5dcc5",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:94f49a7afedbb29d237891f6c4039db2e73960d3a02499a66b4158e36e18119f",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.10.10"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:94f49a7afedbb29d237891f6c4039db2e73960d3a02499a66b4158e36e18119f",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.10.10"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '844317793,'],
        ['"VirtualSize":', '844317793,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/f462e5d20c8846ecbbfa9a4d1abbe03ad9bf8f959a8dc8f326d4eae94a70f447/diff:/var/lib/docker/overlay2/08e92e20143175575f5447cda75099d9d2e8334c5b5a5d8299a05506d9f0e552/diff:/var/lib/docker/overlay2/57a3ac4339c995817c72740187320954374a45c2c8e70aeb6c6fcb8718b42682/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/026c5deaa5ef3639754dd54693a1ef404a1f8e40c47cddb2259ca4f3e97f231b/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/026c5deaa5ef3639754dd54693a1ef404a1f8e40c47cddb2259ca4f3e97f231b/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/026c5deaa5ef3639754dd54693a1ef404a1f8e40c47cddb2259ca4f3e97f231b/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:ab6859e84cc3b28c9b569fe4ce2b0f8547f69b0118039d144074612ebfc86256",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:ed1d4ed4803755a33ac756df9f2580ae3832ffb43fd92d6f22cf657b778825a9",'],
        ['"sha256:033a5aec8ed8c79a7ca929e4592716ca5a728c695482043aa22d4e318a499b11"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-10-10T08:43:17.203196121+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:df118e583614f41d5f190ced1a344ee3ccce2c36e91caf795d78e3c01d906701",'],
        ['"RepoTags":', '[],'], ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:d4c95e27986c20a707d4f943040da6b4ec79991adbf3bd3795036153eccf4663",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-10-10T06:37:26.88476067Z",'],
        ['"Container":', '"6fe73b950209eec37d263057b38fd5e782633f2604f303cbb50c709fa213a2fa",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"6fe73b950209",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:d4c95e27986c20a707d4f943040da6b4ec79991adbf3bd3795036153eccf4663",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0p5"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:d4c95e27986c20a707d4f943040da6b4ec79991adbf3bd3795036153eccf4663",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0p5"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '817561911,'],
        ['"VirtualSize":', '817561911,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/3954ba9bd0b941d70b8d10f32ce86eaacab56357053133aa9cf8372d516b32f5/diff:/var/lib/docker/overlay2/171a9513cdbae0eccf7ac7b9ea5c19a52fb2ae30bba897142c1e03caca08c159/diff:/var/lib/docker/overlay2/0ec8b00e2147cd747e774a814e78c24afea4fe8e1977e95b3df65982015a6aa5/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/517b5eecfccd246bc8e22892f8b06170fbff8a4586f40cf0bb7db0ba77f9e679/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/517b5eecfccd246bc8e22892f8b06170fbff8a4586f40cf0bb7db0ba77f9e679/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/517b5eecfccd246bc8e22892f8b06170fbff8a4586f40cf0bb7db0ba77f9e679/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:3a85589299c0b94b3c1724b36bae516f75984b7b29e873052d8c96ae79e7da94",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:0284e625794b0220dd33ecffc3cb710df5b2ff3728262dedb8635833a5fe81e1",'],
        ['"sha256:033a5aec8ed8c79a7ca929e4592716ca5a728c695482043aa22d4e318a499b11"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-10-10T08:42:22.721533929+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:4a77be28f8e54a4e6a8ecd8cfbd1963463d1e7ac719990206ced057af41e9957",'],
        ['"RepoTags":', '['], ['"checkmk/check-mk-raw:1.5.0p5"'], ['],'], ['"RepoDigests":', '['],
        [
            '"checkmk/check-mk-raw@sha256:afcf4a9f843809598ccb9ddd11a6c415ef465e31969141304e9be57c3e53b438"'
        ], ['],'], ['"Parent":', '"",'], ['"Comment":', '"",'],
        ['"Created":', '"2018-09-28T21:54:16.702903575Z",'],
        ['"Container":', '"c26cf21a0abb0d087ac0d3ff42fa9865fa06778e2e4e021e2c4f34d6a52d373a",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"c26cf21a0abb",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:377f530526c6b6a0c6f9a609662d323a8beb33fdcc7004507ca09fa958884389",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0p5"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:377f530526c6b6a0c6f9a609662d323a8beb33fdcc7004507ca09fa958884389",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0p5"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '751885817,'],
        ['"VirtualSize":', '751885817,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/fcf841c2678358530a6e4c54a4b470c92b6e405501dec99d9f9017c4b719d692/diff:/var/lib/docker/overlay2/5d02afa6ae5354db5d085e7be03f166c370035b088cc8e33971ab97735f398fc/diff:/var/lib/docker/overlay2/782b7f29b434ee2da2e132920e6a337fd2ee715cdfc5e008121eca655b797de0/diff:/var/lib/docker/overlay2/e1354760894f7abc1488535001152c7785baa9406ab38701e0672dff6780cd98/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/bbc63882ef27a4f49162c3f70ddc991f23b452b31846d03a8103e7c2691de42d/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/bbc63882ef27a4f49162c3f70ddc991f23b452b31846d03a8103e7c2691de42d/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/bbc63882ef27a4f49162c3f70ddc991f23b452b31846d03a8103e7c2691de42d/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:a710e8ce658e07af2a635abf0e8d5bd80b036da50f9482c0b7258a640e875ca0",'],
        ['"sha256:03d65c16e5071740137f5135f448886feb99b30ab1556d3b9876db635ac16f9b",'],
        ['"sha256:d237d9e48fb17af4ff6cc6894f166024dbbb3103ad02e1b6b45504785448c263",'],
        ['"sha256:69f1282c62f326711f026b07689648028e17d58c06604429d8c55409f301980c",'],
        ['"sha256:4460e53d99d49e52302d5a107102b0f93ad5a670e9a8d5e7bd96b75af9866b58"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"0001-01-01T00:00:00Z"'], ['}'], ['},'], ['{'],
        ['"Id":', '"sha256:f4bfbb70768f233f1adca8e9e7333695a263773c2663a97732519f3e0eed87b7",'],
        ['"RepoTags":', '['], ['"docker-tests/check-mk-enterprise-master-1.5.0p3:latest"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:a46c70fafb97acdc4643257a07e2290d96ab4242fdfe11e0ae318bcc3c5325f1",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-17T07:47:56.00338337Z",'],
        ['"Container":', '"bbe8233e326b8302e2f4a2dcdc3e7bd4c95eb0a86ecdbb23c7aa996754bfbec0",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"bbe8233e326b",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:a46c70fafb97acdc4643257a07e2290d96ab4242fdfe11e0ae318bcc3c5325f1",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0p3"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:a46c70fafb97acdc4643257a07e2290d96ab4242fdfe11e0ae318bcc3c5325f1",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0p3"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '817394362,'],
        ['"VirtualSize":', '817394362,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/16035e64a82a6f55a5e0876f8b2fbe5c35ef1bb93aa5979aef0680c2488013ac/diff:/var/lib/docker/overlay2/08d4937752d7c6aebcfa07d8e1ba5d2e03f33a8c73cd23cbf5266933b9eebe71/diff:/var/lib/docker/overlay2/80100ea0ace33fdb5ad28be1789ed33c5c54642457317817ab81cad4444efe14/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/c03a524c9b03543dda1c33e6881037331fa4ce03ee649075f7265844035e1122/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/c03a524c9b03543dda1c33e6881037331fa4ce03ee649075f7265844035e1122/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/c03a524c9b03543dda1c33e6881037331fa4ce03ee649075f7265844035e1122/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:4a1700eadae95c7651520e26f35b95333a6d57466fcc48ed71b6f2ee60bf1578",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:31d940abd6efd3f4fc1fbf26814fc34f909ecb3046c7bd1d850f7fb2cc97f52a",'],
        ['"sha256:f666cd41893b4a04d00407db5b8feb54fb1e4b86e75dc96d353ec0ecb9d9d55f"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-17T09:47:56.078067461+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:ff19a3911e0a1560a945c4d749cb47ffd1ca9397f506d195ae8d30a86f46807e",'],
        ['"RepoTags":',
         '['], ['"docker-tests/check-mk-enterprise-master-2018.09.17:latest"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:181350fc92291c5bdb0d36a998a28d1f78854d6be8a052949d99c8095e0af3f8",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-17T07:45:08.855991864Z",'],
        ['"Container":', '"9e3c5c16b60fcb6a98eb0264a0214e9ed863dde9324a67fa151af05996cfe6c1",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"9e3c5c16b60f",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:181350fc92291c5bdb0d36a998a28d1f78854d6be8a052949d99c8095e0af3f8",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.17"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:181350fc92291c5bdb0d36a998a28d1f78854d6be8a052949d99c8095e0af3f8",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.17"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '831431070,'],
        ['"VirtualSize":', '831431070,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/dd17128dba27d5a9e5167fa4acc9c1a35645a4e4130b334b63c284697d6a9793/diff:/var/lib/docker/overlay2/4d5a1fa6cdae22f7231b12f8fc3667e070f28e2eef8385b7a749a88b32929296/diff:/var/lib/docker/overlay2/f6bf7a9cd0c4d34de82a42f74ecf9c7fcff9e29b36cc9fbb7e6e37f2e51b8bfc/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/b949c281b686e76d9a024d51613c7d8b2f1a9164462cdc62a1a798dad931c11d/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/b949c281b686e76d9a024d51613c7d8b2f1a9164462cdc62a1a798dad931c11d/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/b949c281b686e76d9a024d51613c7d8b2f1a9164462cdc62a1a798dad931c11d/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:79d3ac8056c41f305088a1310d90e4e19bdc31b539c44f474465d211bae5c093",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:3bf3aa9eebf3c156fce3efa40136b0f936c702e3e747b42dd7f2772ccd4e6e7d",'],
        ['"sha256:f666cd41893b4a04d00407db5b8feb54fb1e4b86e75dc96d353ec0ecb9d9d55f"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-17T09:48:51.089249505+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:c0582f734ad1bb8c9adaf014c6d0b90ec532bf137afcdb4afe304c0c581ed308",'],
        ['"RepoTags":', '['], ['"checkmk/check-mk-enterprise:2018.09.14"'], ['],'],
        ['"RepoDigests":', '[],'], ['"Parent":', '"",'], ['"Comment":', '"",'],
        ['"Created":', '"2018-09-14T14:52:00.394955469Z",'],
        ['"Container":', '"350a17bbd615ae6a118d29f756385281bc7e0c038cb25ae18fe0c83a8aaece38",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"350a17bbd615",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:6c4f4f10cced68c3cf441948903f5f8fa93655445f33d79632bdd23a9c0840f4",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.14"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:6c4f4f10cced68c3cf441948903f5f8fa93655445f33d79632bdd23a9c0840f4",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.14"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '831425908,'],
        ['"VirtualSize":', '831425908,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/5c7930aaad93d4f38f7d97a060a22b1d6d430f14a705c7de05015cc64d33238d/diff:/var/lib/docker/overlay2/ec9d304d85974f768330893a80c6f7864fe37af3685d5b3518e5b08b5c7e0b67/diff:/var/lib/docker/overlay2/30461fe7b521cc75d2c417449b58cdc0404b1cb8ab1d3b2d4e813238acd9d06d/diff:/var/lib/docker/overlay2/90fe8487f06fff758213b4decbf3753cb5a5a44c7b0e45461e93b47a6550fe9a/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/25f1d9802a55eaca2ab2cd51cec3db94d5e10e96c4bd4251b68033adf7b0f192/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/25f1d9802a55eaca2ab2cd51cec3db94d5e10e96c4bd4251b68033adf7b0f192/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/25f1d9802a55eaca2ab2cd51cec3db94d5e10e96c4bd4251b68033adf7b0f192/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:d07c88abab70ebf0f841a89c89fff9afd87682894118ca0251621e0e5a85d1e2",'],
        ['"sha256:4ebd2a1d59a98435b3a715a2987d54d6fbcccc9903d0ea4be8bcfb927e19fa45",'],
        ['"sha256:54b3888d5a8619d070585739996001b45b4340848fe5326a12dc3ab5ab29336d",'],
        ['"sha256:1e64ea2b32b4827389ac47bdf883cedbdfca555ae3001c93b3a564f364bf3841",'],
        ['"sha256:cac9597f00b1fc42b9f27049b4e6c9675cd46ab82209abb64a681160d90e6aeb"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"0001-01-01T00:00:00Z"'], ['}'], ['},'], ['{'],
        ['"Id":', '"sha256:91152cc1c4bcd3aba6309d88b2c2a7e53f2e6209757f3fda180489f064994287",'],
        ['"RepoTags":',
         '['], ['"docker-tests/check-mk-enterprise-master-2018.09.14:latest"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:688325a00909823baa9ed3d50f5ef4ed16abb44e519bb80b32efcbf221daaa8c",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-14T12:47:41.138435628Z",'],
        ['"Container":', '"c2d5801472813250dc1f463c618218dc9414361de5a72715991fbc55073b54af",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"c2d580147281",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:688325a00909823baa9ed3d50f5ef4ed16abb44e519bb80b32efcbf221daaa8c",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.14"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:688325a00909823baa9ed3d50f5ef4ed16abb44e519bb80b32efcbf221daaa8c",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.14"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '831425899,'],
        ['"VirtualSize":', '831425899,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/8a31efb917fa1a8f5a724fb770736b3e6c6d2d729956b9bd70eee53c61158e0c/diff:/var/lib/docker/overlay2/79c02f0f9ea3ab21bdb65b3845bb71085679bab3cf8a0ed4f65c0bf1099e1536/diff:/var/lib/docker/overlay2/948e2b556ef829021d6b815ae8498ae2c96c5302b5a31123202482c446e26aac/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/1d20cd960496335a8ccacae8d2a5f2df69834528933a8cf33c0992d20b4445d4/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/1d20cd960496335a8ccacae8d2a5f2df69834528933a8cf33c0992d20b4445d4/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/1d20cd960496335a8ccacae8d2a5f2df69834528933a8cf33c0992d20b4445d4/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:9cdc314563df2462ed6e1296a8ca33b91a444e1a87837d094b18f097b79e6f6e",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:ec7505c27857ca932d3a0d6d03e072053d9b6cec0c940ef7c6483c4b52b6fc28",'],
        ['"sha256:64023ab8f398c564117ef7b2f564482fdfe6102e2b649e774261e8b75d14fb82"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-14T14:47:41.201321168+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:8ca14ae84dd9a788bcaddd196cbed346d6cd624fa1a63253728df769e26d2a21",'],
        ['"RepoTags":', '['], ['"checkmk/check-mk-enterprise:daily"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:ab07946db07bd7c6f0b0360f5dd33558cc1d95afe78e6b367f997795d3bc09e3",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-14T11:08:54.79214559Z",'],
        ['"Container":', '"1d198344cbda4b5eda59ff5219264d2eba68db0aec079a70ec29849db976d253",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"1d198344cbda",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:ab07946db07bd7c6f0b0360f5dd33558cc1d95afe78e6b367f997795d3bc09e3",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.14"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:ab07946db07bd7c6f0b0360f5dd33558cc1d95afe78e6b367f997795d3bc09e3",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.14"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '972256089,'],
        ['"VirtualSize":', '972256089,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/679258c4e3207075892b04d0373c085e0a7d6e4bbac8867afb992fdeb276f3ba/diff:/var/lib/docker/overlay2/2b287fc6c88af8fe6c4ceb2ca6d2a5fec6dd275ab7764035eed891237ade01b7/diff:/var/lib/docker/overlay2/61f56caf072a07ba2daf241215beed7d903cb45d045c1cf60155d7240f4d741c/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/1dde02f2d25b45c1521b11a921396e8a434a79999bdd3411fa5b44d058751ac0/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/1dde02f2d25b45c1521b11a921396e8a434a79999bdd3411fa5b44d058751ac0/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/1dde02f2d25b45c1521b11a921396e8a434a79999bdd3411fa5b44d058751ac0/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:ede3d7d3b30242493d40eb33255e7a9075399888f34d10971e95208fa79cc3d0",'],
        ['"sha256:897069ab5f160c17c99aa550b57da6ac8ff573f0a01d994044461c80248a8358",'],
        ['"sha256:4aef980cbccf2f4cfa2935f327c08eccf3e2fa8674699eaa15411ad22f39b280",'],
        ['"sha256:39ef0a6b7527ea43c2df1bbe2f4a1e9f0406e0579a56bb9798ef3c7226b0eca5"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-14T13:08:54.928277438+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:44a5d6d152722adef8dada252863f178993d955b49caa8ea7b954d9ebc93b1c2",'],
        ['"RepoTags":', '['], ['"checkmk/check-mk-enterprise:1.5.0-2018.09.14",'],
        ['"checkmk/check-mk-enterprise:1.5.0-daily"'], ['],'], ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:f4b9edc5ccef68a90483ba6272dd766abdbfd4eef84e751fbfb70942f490983e",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-14T10:45:50.232853938Z",'],
        ['"Container":', '"cc6d51f658420cfa70f0b8323a95090da5f76569e3815be6d2ef729c0cb7bb71",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"cc6d51f65842",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:f4b9edc5ccef68a90483ba6272dd766abdbfd4eef84e751fbfb70942f490983e",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0-2018.09.14"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:f4b9edc5ccef68a90483ba6272dd766abdbfd4eef84e751fbfb70942f490983e",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0-2018.09.14"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '817965472,'],
        ['"VirtualSize":', '817965472,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/1789a2bbcfe6630a10e16da6cdb3848be2eda885067017ff23fb8b8925f92c8f/diff:/var/lib/docker/overlay2/7bc6e2eb7593a16fe46516ff82bc2e791db9c10858279b4c29efb144b18a3d77/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/4077601dd3f9e280b1868e0f233ffe0fbff6d80f2b4ed2e7329b9572d8759ed7/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/4077601dd3f9e280b1868e0f233ffe0fbff6d80f2b4ed2e7329b9572d8759ed7/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/4077601dd3f9e280b1868e0f233ffe0fbff6d80f2b4ed2e7329b9572d8759ed7/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:b27afe80d76f912e7d0b8ce74f3246beac6b18555fba067fe2a6bbd93a46cd43",'],
        ['"sha256:b9b2e4dcc9f2ea38ebc0b6602c6d104de65f515cb9304be29b916dd99dfe4e46",'],
        ['"sha256:39ef0a6b7527ea43c2df1bbe2f4a1e9f0406e0579a56bb9798ef3c7226b0eca5"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-14T12:45:50.356637867+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:44a5d6d152722adef8dada252863f178993d955b49caa8ea7b954d9ebc93b1c2",'],
        ['"RepoTags":', '['], ['"checkmk/check-mk-enterprise:1.5.0-2018.09.14",'],
        ['"checkmk/check-mk-enterprise:1.5.0-daily"'], ['],'], ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:f4b9edc5ccef68a90483ba6272dd766abdbfd4eef84e751fbfb70942f490983e",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-14T10:45:50.232853938Z",'],
        ['"Container":', '"cc6d51f658420cfa70f0b8323a95090da5f76569e3815be6d2ef729c0cb7bb71",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"cc6d51f65842",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:f4b9edc5ccef68a90483ba6272dd766abdbfd4eef84e751fbfb70942f490983e",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0-2018.09.14"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:f4b9edc5ccef68a90483ba6272dd766abdbfd4eef84e751fbfb70942f490983e",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0-2018.09.14"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '817965472,'],
        ['"VirtualSize":', '817965472,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/1789a2bbcfe6630a10e16da6cdb3848be2eda885067017ff23fb8b8925f92c8f/diff:/var/lib/docker/overlay2/7bc6e2eb7593a16fe46516ff82bc2e791db9c10858279b4c29efb144b18a3d77/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/4077601dd3f9e280b1868e0f233ffe0fbff6d80f2b4ed2e7329b9572d8759ed7/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/4077601dd3f9e280b1868e0f233ffe0fbff6d80f2b4ed2e7329b9572d8759ed7/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/4077601dd3f9e280b1868e0f233ffe0fbff6d80f2b4ed2e7329b9572d8759ed7/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:b27afe80d76f912e7d0b8ce74f3246beac6b18555fba067fe2a6bbd93a46cd43",'],
        ['"sha256:b9b2e4dcc9f2ea38ebc0b6602c6d104de65f515cb9304be29b916dd99dfe4e46",'],
        ['"sha256:39ef0a6b7527ea43c2df1bbe2f4a1e9f0406e0579a56bb9798ef3c7226b0eca5"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-14T12:45:50.356637867+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:2e89feac75330553688011dfb2efc0f9c6e44b61a419d937ad826c8628007e10",'],
        ['"RepoTags":',
         '['], ['"docker-tests/check-mk-enterprise-master-2018.09.13:latest"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:1279a98be898d5d9834447b7f9effb4209ce7ad72ce0ada70eef2a76fc8deb30",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-13T06:27:42.955259674Z",'],
        ['"Container":', '"e9a579ff3eeffd9bfd753f72d55e795a0edbb2cf2eac6c7aabc0c91d8f2973f2",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"e9a579ff3eef",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:1279a98be898d5d9834447b7f9effb4209ce7ad72ce0ada70eef2a76fc8deb30",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.13"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:1279a98be898d5d9834447b7f9effb4209ce7ad72ce0ada70eef2a76fc8deb30",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.13"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '831418094,'],
        ['"VirtualSize":', '831418094,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/0e7b12e20ba3734ef8ab9dd29ad6bee25a55ba705721b6a37a88413605bdd1cb/diff:/var/lib/docker/overlay2/c738dff51d236a0350a064cd029322ad160932cadc4d21950c5fcd49f6c6fedd/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/5df283bcfef3e520b9ae83dbf07944a1ae0c684062357e854990531481a6c921/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/5df283bcfef3e520b9ae83dbf07944a1ae0c684062357e854990531481a6c921/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/5df283bcfef3e520b9ae83dbf07944a1ae0c684062357e854990531481a6c921/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:220a4fe8fd8039e1d45471aa6bc85054e6deaf3ad277a58906b1544b24f3bfc5",'],
        ['"sha256:f7544a3f89a4a87060320001eba709eb401228824eb4a195a00f4dee134d2b99",'],
        ['"sha256:1331a4d6e607b0f40b6ae209186957331b295ce7fadcf3329e0906325ae22244"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-13T09:32:20.480334061+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:096300fde75dddfb273b343aa94957dffdbb4b57212debaddbd6f7714442df57",'],
        ['"RepoTags":', '['], ['"checkmk/check-mk-enterprise:1.5.0-2018.09.13"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:6c7d657ff8143bed866d393682ed6da9d1da9ff3eba3906332c19b7078659ac6",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-13T06:15:30.34090448Z",'],
        ['"Container":', '"f0df7d7d996959b3c8b01602ae9cb21fa2f24c9a374fc6ee2d6afff1694cd253",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"f0df7d7d9969",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:6c7d657ff8143bed866d393682ed6da9d1da9ff3eba3906332c19b7078659ac6",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0-2018.09.13"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:6c7d657ff8143bed866d393682ed6da9d1da9ff3eba3906332c19b7078659ac6",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0-2018.09.13"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '817961530,'],
        ['"VirtualSize":', '817961530,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/8bcd764ee6df9efa6336c1143afeb4ad7c85d5d68413a96295ba4f737e6c797f/diff:/var/lib/docker/overlay2/e1f9dcd3fdc5c19af722e2d6c941b0cdce6cb61ce6be758eeb909f9b78cdc75c/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/c5901c97861df0eb207a9fd1005c7a69dd02fd2f44c59d1f444ba39708acf771/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/c5901c97861df0eb207a9fd1005c7a69dd02fd2f44c59d1f444ba39708acf771/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/c5901c97861df0eb207a9fd1005c7a69dd02fd2f44c59d1f444ba39708acf771/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:436af26c102cce64fe6331797787d13de5cee7590fb9729dcff575f29fe21491",'],
        ['"sha256:4f14b365e2206439394a6a51a395a1bb6f5987760c9824d064e18b46ec0d98cc",'],
        ['"sha256:1331a4d6e607b0f40b6ae209186957331b295ce7fadcf3329e0906325ae22244"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-13T08:15:30.458557512+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:8d463a5f7635ebd0c6f418236c571273083e1c5bc63711a2babc4048208f9aa3",'],
        ['"RepoTags":', '['], ['"checkmk/check-mk-enterprise:1.5.0-2018.09.12"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:8cf1aa71b39c4ca824aebd5c20b0790750add56e5aa18b8f01408f3bba629942",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-12T19:15:47.455944537Z",'],
        ['"Container":', '"7008e2438630103ef35fe39e9b0e4032d9fd01a8f9088a38d73be87c9c6c352d",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"7008e2438630",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:8cf1aa71b39c4ca824aebd5c20b0790750add56e5aa18b8f01408f3bba629942",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0-2018.09.12"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:8cf1aa71b39c4ca824aebd5c20b0790750add56e5aa18b8f01408f3bba629942",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"1.5.0-2018.09.12"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '814907653,'],
        ['"VirtualSize":', '814907653,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/e8ff9d186625aaba8cde8c906d2a1fb3af4bb95a0d80011c9fa51c9ed8338f1e/diff:/var/lib/docker/overlay2/b41ef1a633d4429502cb4dba72513b7aad9e2a6ebb8dc9d559069dc9ea8d4f9c/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/7667200074de72b2270a1c44bcc7dd59fbef7689ec8c053aa47cd134c6ab6eb1/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/7667200074de72b2270a1c44bcc7dd59fbef7689ec8c053aa47cd134c6ab6eb1/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/7667200074de72b2270a1c44bcc7dd59fbef7689ec8c053aa47cd134c6ab6eb1/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:f7c63d2fb8606a0f1811e661f36cb8dfa6e013da31bb4e7d3ddd8020cdbc0fea",'],
        ['"sha256:9295f12e0264404aff0eaea5261ea6a5d137ade10d9013214a02247b13ce8d5e",'],
        ['"sha256:1331a4d6e607b0f40b6ae209186957331b295ce7fadcf3329e0906325ae22244"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-12T21:15:47.570548036+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:a1f15f9a2b1640ac73437fc96b658b7c9907ab14127e1ec82cd93986874e3159",'],
        ['"RepoTags":',
         '['], ['"docker-tests/check-mk-enterprise-master-2018.09.12:latest"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:699b9ae110ea244e88162a74fb311a1147e28ca3ef3ff3f1b871c866ab54699d",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-12T17:49:54.487390036Z",'],
        ['"Container":', '"070fa69b45954fa2c09a2fbb5bcc3d876635c8f73d4b0645cc89c9b89c3b515a",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"070fa69b4595",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:699b9ae110ea244e88162a74fb311a1147e28ca3ef3ff3f1b871c866ab54699d",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.12"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:699b9ae110ea244e88162a74fb311a1147e28ca3ef3ff3f1b871c866ab54699d",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.12"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '828361723,'],
        ['"VirtualSize":', '828361723,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/f4af279c0133af9a4dc28d967d4917f24e0d3fb7213f42ed816e830ba800d4da/diff:/var/lib/docker/overlay2/b3aa070146057965e76a8d2222c99281f8608c521629983c3d18419cce68fa8d/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/2ca15fa9aaf60059f35ef8e20c068a07b8da81af0c357087a376edc500bdd8ef/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/2ca15fa9aaf60059f35ef8e20c068a07b8da81af0c357087a376edc500bdd8ef/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/2ca15fa9aaf60059f35ef8e20c068a07b8da81af0c357087a376edc500bdd8ef/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'],
        ['"sha256:99295c6b8aa9b55a40e44d760d1175d349b9d5fc5e71d1897b0d7c1d80f0ade6",'],
        ['"sha256:ea6f372505b88d8a69f838f131b8c233e382881a7fe58cf69162781c3faaf159",'],
        ['"sha256:1331a4d6e607b0f40b6ae209186957331b295ce7fadcf3329e0906325ae22244"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-12T19:51:06.184241414+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:ee5124a3adb5eb20012a7189ea34495da3e39ff8517c2c260954654d3edf1553",'],
        ['"RepoTags":',
         '['], ['"docker-tests/check-mk-enterprise-master-2018.09.11:latest"'], ['],'],
        ['"RepoDigests":', '[],'],
        ['"Parent":', '"sha256:38acc2cecea17dc893309f5b91c080b3eda7bbcd922ad240065ab34f677390ca",'],
        ['"Comment":', '"",'], ['"Created":', '"2018-09-12T07:33:22.502880318Z",'],
        ['"Container":', '"8523e3046688f64bedf5f580f73b5fefa5d038b96bc418c5ddca9b7bfb4997fc",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"8523e3046688",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'],
        ['"6557/tcp":', '{}'], ['},'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":',
                                         '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"ENTRYPOINT', '[\\"/docker-entrypoint.sh\\"]"'], ['],'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:38acc2cecea17dc893309f5b91c080b3eda7bbcd922ad240065ab34f677390ca",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.11"'], ['}'], ['},'],
        ['"DockerVersion":', '"18.06.1-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"ExposedPorts":', '{'], ['"5000/tcp":', '{},'], ['"6557/tcp":', '{}'], ['},'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['"CMK_SITE_ID=cmk",'], ['"CMK_LIVESTATUS_TCP=",'], ['"CMK_PASSWORD=",'],
        ['"MAIL_RELAY_HOST="'], ['],'], ['"Cmd":', 'null,'], ['"Healthcheck":', '{'],
        ['"Test":', '['], ['"CMD-SHELL",'], ['"omd', 'status', '||', 'exit', '1"'], ['],'],
        ['"Interval":', '60000000000,'], ['"Timeout":', '5000000000'], ['},'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:38acc2cecea17dc893309f5b91c080b3eda7bbcd922ad240065ab34f677390ca",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', '['],
        ['"/docker-entrypoint.sh"'], ['],'], ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"maintainer":', '"feedback@checkmk.com",'],
        [
            '"org.opencontainers.image.description":', '"Check_MK', 'is', 'a', 'leading', 'tool',
            'for', 'Infrastructure', '&', 'Application', 'Monitoring",'
        ], ['"org.opencontainers.image.source":', '"https://github.com/tribe29/checkmk",'],
        ['"org.opencontainers.image.title":', '"Checkmk",'],
        ['"org.opencontainers.image.url":', '"https://checkmk.com/",'],
        ['"org.opencontainers.image.vendor":', '"tribe29', 'GmbH",'],
        ['"org.opencontainers.image.version":', '"2018.09.11"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '828358667,'],
        ['"VirtualSize":', '828358667,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"LowerDir":',
            '"/var/lib/docker/overlay2/95fe09c1003cb37acd45a31572f4085ce97a9f072642002885497842913070de/diff:/var/lib/docker/overlay2/d02bfc44bf45c738d94cb54a9226eedae3372e8c3b1b09179d74ebee4f7163fb/diff:/var/lib/docker/overlay2/34d99e5b1542b9c1153a3ea1a514529e5f1953388a00f9cda857e60424eea355/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/fdd27ec5c8b6c4c5d44d4df62deff2f36b0e39a5143ee41b2b6d8668050785fb/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/fdd27ec5c8b6c4c5d44d4df62deff2f36b0e39a5143ee41b2b6d8668050785fb/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/fdd27ec5c8b6c4c5d44d4df62deff2f36b0e39a5143ee41b2b6d8668050785fb/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":', '['],
        ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'],
        ['"sha256:db03f598b3e36870108f3534053062e71157bb6d9f853a60f32b51a179e705f3",'],
        ['"sha256:52629a4c156e647f5b3a12760bade7c060c96aff69dda830393b4cfa32c519dd",'],
        ['"sha256:ea9ae40f80db03b02b7fa4e5228f1605573a7fb081a1dec013d0271e594d9723",'],
        ['"sha256:97c9fb22e0981305ded9bb2b7419bd5a9a1b8621c7d62dab2705813bd5053882"'], [']'], [
            '},'
        ], ['"Metadata":', '{'], ['"LastTagTime":', '"2018-09-12T09:37:58.237253932+02:00"'], ['}'],
        ['},'], ['{'],
        ['"Id":', '"sha256:6143303a8e14d19961946d8749b698e2d1a90262c62a11dee5a40367907afe88",'],
        ['"RepoTags":', '['], ['"hadolint/hadolint:latest"'], ['],'], ['"RepoDigests":', '['],
        [
            '"hadolint/hadolint@sha256:513b14db75c5fa4f7b6b2376f51fcdf4c29705b9532dae47e63ec6ae9ad224ad"'
        ], ['],'], ['"Parent":', '"",'], ['"Comment":', '"",'],
        ['"Created":', '"2018-09-10T15:36:25.80531779Z",'],
        ['"Container":', '"49883050656a6f9ddc62dbc637c0215cdf52c061718038c2bc8996a35090dc4f",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"49883050656a",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"'], ['],'],
        ['"Cmd":', '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'],
        ['"CMD', '[\\"/bin/hadolint\\"', '\\"-\\"]"'], ['],'], ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:51716346795e3bf5c3945a70afc6eb143d6f54be35c72e92f63d8aee0d7c068f",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', 'null,'],
        ['"OnBuild":', 'null,'], ['"Labels":', '{}'], ['},'],
        ['"DockerVersion":', '"18.03.1-ee-1-tp5",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"'], ['],'],
        ['"Cmd":', '['], ['"/bin/hadolint",'], ['"-"'], ['],'], ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:51716346795e3bf5c3945a70afc6eb143d6f54be35c72e92f63d8aee0d7c068f",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', 'null,'],
        ['"OnBuild":', 'null,'], ['"Labels":', 'null'], ['},'], ['"Architecture":', '"amd64",'],
        ['"Os":', '"linux",'], ['"Size":', '3644760,'], ['"VirtualSize":', '3644760,'],
        ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/d8101a8e05225b4007a60a4be9c77b9efa72bf702b3cd38ea72619db66db1b47/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/d8101a8e05225b4007a60a4be9c77b9efa72bf702b3cd38ea72619db66db1b47/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/d8101a8e05225b4007a60a4be9c77b9efa72bf702b3cd38ea72619db66db1b47/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":',
         '['], ['"sha256:7e9956eca1ab8e60764d827f0ccc7b9271e768757139603b1d2a9b7a35e6fa4f"'], [']'],
        ['},'], ['"Metadata":', '{'], ['"LastTagTime":', '"0001-01-01T00:00:00Z"'], ['}'], ['},'],
        ['{'],
        ['"Id":', '"sha256:44e19a16bde1fd0f00b8cfb2b816e329ddee5c79869d140415f4445df4da485c",'],
        ['"RepoTags":', '['], ['"debian:stretch-slim"'], ['],'], ['"RepoDigests":', '['],
        ['"debian@sha256:40b4072ce18fabe32f357f7c9ec1d256d839b1b95bcdc1f9c910823c6c2932e9"'], [
            '],'
        ], ['"Parent":', '"",'], ['"Comment":', '"",'],
        ['"Created":', '"2018-09-04T21:21:34.566479261Z",'],
        ['"Container":', '"4229f492c8b05d2f6eda40e7b61be851a4160f9b1350fa4445ac51db802e7240",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"4229f492c8b0",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"'], ['],'],
        ['"Cmd":', '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)', '",'], ['"CMD', '[\\"bash\\"]"'],
        ['],'], ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:6c23807240a4e57fb973aa9f9c5ab08d5c0f2141afc913efb7049b1bd96e300f",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', 'null,'],
        ['"OnBuild":', 'null,'], ['"Labels":', '{}'], ['},'], ['"DockerVersion":', '"17.06.2-ce",'],
        ['"Author":', '"",'], ['"Config":', '{'], ['"Hostname":', '"",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"'], ['],'],
        ['"Cmd":', '['], ['"bash"'], ['],'], ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:6c23807240a4e57fb973aa9f9c5ab08d5c0f2141afc913efb7049b1bd96e300f",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', 'null,'],
        ['"OnBuild":', 'null,'], ['"Labels":', 'null'], ['},'], ['"Architecture":', '"amd64",'],
        ['"Os":', '"linux",'], ['"Size":', '55270217,'], ['"VirtualSize":', '55270217,'],
        ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":',
         '['], ['"sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817"'], [']'],
        ['},'], ['"Metadata":', '{'], ['"LastTagTime":', '"0001-01-01T00:00:00Z"'], ['}'], ['},'],
        ['{'],
        ['"Id":', '"sha256:5182e96772bf11f4b912658e265dfe0db8bd314475443b6434ea708784192892",'],
        ['"RepoTags":', '['], ['"centos:7"'], ['],'], ['"RepoDigests":', '['],
        ['"centos@sha256:6f6d986d425aeabdc3a02cb61c02abb2e78e57357e92417d6d58332856024faf"'], [
            '],'
        ], ['"Parent":', '"",'], ['"Comment":', '"",'],
        ['"Created":', '"2018-08-06T19:21:48.235227329Z",'],
        ['"Container":', '"d60ffc9ddd12462af4bdcdbe45b74f3b3f99b46607ada80c3ed877b7def84250",'],
        ['"ContainerConfig":', '{'], ['"Hostname":', '"d60ffc9ddd12",'], ['"Domainname":', '"",'],
        ['"User":', '"",'], ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'],
        ['"AttachStderr":', 'false,'], ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'],
        ['"StdinOnce":', 'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"'], ['],'],
        ['"Cmd":', '['], ['"/bin/sh",'], ['"-c",'], ['"#(nop)',
                                                     '",'], ['"CMD', '[\\"/bin/bash\\"]"'], ['],'],
        ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:748eacc0f236df2fc9ba87c4d76a66cb10742120387e99e2acdb9454915c841d",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', 'null,'],
        ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"org.label-schema.build-date":', '"20180804",'],
        ['"org.label-schema.license":', '"GPLv2",'],
        ['"org.label-schema.name":', '"CentOS', 'Base', 'Image",'],
        ['"org.label-schema.schema-version":',
         '"1.0",'], ['"org.label-schema.vendor":', '"CentOS"'], ['}'], ['},'],
        ['"DockerVersion":', '"17.06.2-ce",'], ['"Author":', '"",'], ['"Config":', '{'],
        ['"Hostname":', '"",'], ['"Domainname":', '"",'], ['"User":', '"",'],
        ['"AttachStdin":', 'false,'], ['"AttachStdout":', 'false,'], ['"AttachStderr":', 'false,'],
        ['"Tty":', 'false,'], ['"OpenStdin":', 'false,'], ['"StdinOnce":',
                                                           'false,'], ['"Env":', '['],
        ['"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"'], ['],'],
        ['"Cmd":', '['], ['"/bin/bash"'], ['],'], ['"ArgsEscaped":', 'true,'],
        ['"Image":', '"sha256:748eacc0f236df2fc9ba87c4d76a66cb10742120387e99e2acdb9454915c841d",'],
        ['"Volumes":', 'null,'], ['"WorkingDir":', '"",'], ['"Entrypoint":', 'null,'],
        ['"OnBuild":', 'null,'], ['"Labels":', '{'],
        ['"org.label-schema.build-date":', '"20180804",'],
        ['"org.label-schema.license":', '"GPLv2",'],
        ['"org.label-schema.name":', '"CentOS', 'Base', 'Image",'],
        ['"org.label-schema.schema-version":',
         '"1.0",'], ['"org.label-schema.vendor":', '"CentOS"'], ['}'], ['},'],
        ['"Architecture":', '"amd64",'], ['"Os":', '"linux",'], ['"Size":', '199723824,'],
        ['"VirtualSize":', '199723824,'], ['"GraphDriver":', '{'], ['"Data":', '{'],
        [
            '"MergedDir":',
            '"/var/lib/docker/overlay2/1727960010f698e148cb98e9cf81d09ea52537deba2f7be30bc80e940f54562e/merged",'
        ],
        [
            '"UpperDir":',
            '"/var/lib/docker/overlay2/1727960010f698e148cb98e9cf81d09ea52537deba2f7be30bc80e940f54562e/diff",'
        ],
        [
            '"WorkDir":',
            '"/var/lib/docker/overlay2/1727960010f698e148cb98e9cf81d09ea52537deba2f7be30bc80e940f54562e/work"'
        ], ['},'], ['"Name":', '"overlay2"'], ['},'], ['"RootFS":', '{'], ['"Type":', '"layers",'],
        ['"Layers":',
         '['], ['"sha256:1d31b5806ba40b5f67bde96f18a181668348934a44c9253b420d5f04cfb4e37a"'], [']'],
        ['},'], ['"Metadata":', '{'], ['"LastTagTime":', '"0001-01-01T00:00:00Z"'], ['}'], ['}'],
        [']'], []
    ],
    'containers': [
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:12:19', '+0200',
            'CEST","ID":"802786d33cfb","Image":"010bad2c964b","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"boring_cori","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(100)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '16:12:02', '+0200',
            'CEST","ID":"11893c5d9694","Image":"559214f8c758","Labels":"maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5","LocalVolumes":"0","Mounts":"","Names":"affectionate_shannon","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '16:12:02', '+0200',
            'CEST","ID":"95796d6d26db","Image":"fcd54dfcb5b8","Labels":"org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/","LocalVolumes":"0","Mounts":"","Names":"distracted_heisenberg","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '16:12:01', '+0200',
            'CEST","ID":"58ea2160fe8f","Image":"3bd4e802a09f","Labels":"org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk","LocalVolumes":"0","Mounts":"","Names":"lucid_kowalevski","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '16:12:01', '+0200',
            'CEST","ID":"74ee5065acb2","Image":"a0529d041d12","Labels":"org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk","LocalVolumes":"0","Mounts":"","Names":"peaceful_joliot","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:11:24', '+0200',
            'CEST","ID":"7db7baa17fee","Image":"fd98c3cc9762","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"stoic_jennings","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:09:34', '+0200',
            'CEST","ID":"249ca074445f","Image":"010bad2c964b","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"infallible_goodall","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:07:29', '+0200',
            'CEST","ID":"63c0ad8e9eb7","Image":"0983f5184ce7","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"ecstatic_babbage","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(1)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-12', '16:05:44', '+0200',
            'CEST","ID":"d91a2be75e8b","Image":"010bad2c964b","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"jovial_bardeen","Networks":"bridge","Ports":"","RunningFor":"3',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/usr/sbin/init\\"","CreatedAt":"2018-10-12', '11:13:24', '+0200',
            'CEST","ID":"f1641e401237","Image":"local/c7-systemd-httpd","Labels":"org.label-schema.schema-version=1.0,org.label-schema.vendor=CentOS,org.label-schema.build-date=20180804,org.label-schema.license=GPLv2,org.label-schema.name=CentOS',
            'Base',
            'Image","LocalVolumes":"0","Mounts":"/sys/fs/cgroup","Names":"sad_stonebraker","Networks":"bridge","Ports":"","RunningFor":"4',
            'days', 'ago","Size":"0B","Status":"Exited', '(137)', '3', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/usr/sbin/init\\"","CreatedAt":"2018-10-12', '11:13:18', '+0200',
            'CEST","ID":"7d32581dd10f","Image":"local/c7-systemd-httpd","Labels":"org.label-schema.build-date=20180804,org.label-schema.license=GPLv2,org.label-schema.name=CentOS',
            'Base',
            'Image,org.label-schema.schema-version=1.0,org.label-schema.vendor=CentOS","LocalVolumes":"0","Mounts":"/sys/fs/cgroup","Names":"sad_austin","Networks":"bridge","Ports":"","RunningFor":"4',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.\xe2\x80\xa6\\"","CreatedAt":"2018-10-12',
            '09:17:54', '+0200',
            'CEST","ID":"fdd04795069e","Image":"checkmk/check-mk-raw:1.5.0p5","Labels":"org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/","LocalVolumes":"1","Mounts":"/etc/localtime,10b7c962177bf2\xe2\x80\xa6","Names":"monitoringx","Networks":"bridge","Ports":"6557/tcp,',
            '0.0.0.0:8080-\\u003e5000/tcp","RunningFor":"4', 'days',
            'ago","Size":"0B","Status":"Up', '6', 'hours', '(healthy)"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:40:21', '+0200',
            'CEST","ID":"b17185d5dcc5","Image":"94f49a7afedb","Labels":"org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk","LocalVolumes":"0","Mounts":"","Names":"friendly_banach","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:40:20', '+0200',
            'CEST","ID":"73237ecc5183","Image":"d27276979703","Labels":"org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/","LocalVolumes":"0","Mounts":"","Names":"festive_stallman","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:40:20', '+0200',
            'CEST","ID":"0d7e34ebb911","Image":"03d98e475cd6","Labels":"org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"youthful_pare","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:40:20', '+0200',
            'CEST","ID":"580a7b4bd20a","Image":"3e0dd44b22e4","Labels":"org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=2018.10.10,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring","LocalVolumes":"0","Mounts":"","Names":"reverent_proskuriakova","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10', '08:39:29', '+0200',
            'CEST","ID":"4a6806b168b1","Image":"089108b69108","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"festive_fermi","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '6', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10', '08:37:43', '+0200',
            'CEST","ID":"93e0c88a69fa","Image":"b16a30c66821","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"objective_darwin","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '6', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/docker-entrypoint.\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:37:26', '+0200',
            'CEST","ID":"6fe73b950209","Image":"d4c95e27986c","Labels":"org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk","LocalVolumes":"0","Mounts":"","Names":"admiring_haibt","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:37:26', '+0200',
            'CEST","ID":"bfdb64ccf0ba","Image":"21b2f3d5e6c0","Labels":"maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5","LocalVolumes":"0","Mounts":"","Names":"lucid_bohr","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:37:25', '+0200',
            'CEST","ID":"24772268cc09","Image":"6e66f5473958","Labels":"org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring,org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk","LocalVolumes":"0","Mounts":"","Names":"zen_bartik","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:37:25', '+0200',
            'CEST","ID":"8f8ded35fc90","Image":"6bccd8c3ed71","Labels":"org.opencontainers.image.source=https://github.com/tribe29/checkmk,org.opencontainers.image.title=Checkmk,org.opencontainers.image.url=https://checkmk.com/,org.opencontainers.image.vendor=tribe29',
            
            'GmbH,org.opencontainers.image.version=1.5.0p5,maintainer=feedback@checkmk.com,org.opencontainers.image.description=Check_MK',
            'is', 'a', 'leading', 'tool', 'for', 'Infrastructure', '\\u0026', 'Application',
            'Monitoring","LocalVolumes":"0","Mounts":"","Names":"keen_cori","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10', '08:36:45', '+0200',
            'CEST","ID":"a073bb9adfbe","Image":"7aa4b82c92ae","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"jovial_archimedes","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '6', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'set", '-e',
            '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10', '08:34:58', '+0200',
            'CEST","ID":"4d4d9f3be74b","Image":"b16a30c66821","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"pensive_spence","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Exited', '(0)', '6', 'days', 'ago"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:58', '+0200',
            'CEST","ID":"df44340ed121","Image":"1b013e043efa","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"unruffled_hopper","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:58', '+0200',
            'CEST","ID":"860d8dfff4f6","Image":"7e7f944ba518","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"dazzling_meninsky","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:57', '+0200',
            'CEST","ID":"a17f21f95383","Image":"a2a187fcaa76","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"serene_poincare","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:57', '+0200',
            'CEST","ID":"6cae82f879ff","Image":"1d9b21b9e019","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"elated_poitras","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:57', '+0200',
            'CEST","ID":"aad80d524200","Image":"e002e37aec84","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"competent_keller","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:56', '+0200',
            'CEST","ID":"d1c70f4690b5","Image":"0b5da1249a04","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"trusting_panini","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:56', '+0200',
            'CEST","ID":"9b08cf26da8c","Image":"164429e47a3f","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"pensive_swartz","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:56', '+0200',
            'CEST","ID":"c04099ed3f18","Image":"d1a41c564864","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"dreamy_thompson","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:56', '+0200',
            'CEST","ID":"cdc7e1e4a24e","Image":"999fc035fc76","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"lucid_brown","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:55', '+0200',
            'CEST","ID":"10d6b884f348","Image":"a0a951b126eb","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"wizardly_ritchie","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:55', '+0200',
            'CEST","ID":"d37198a74c08","Image":"caac4aa6ac57","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"distracted_mccarthy","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/sh', '-c', "'#(nop)", '\xe2\x80\xa6\\"","CreatedAt":"2018-10-10',
            '08:34:55', '+0200',
            'CEST","ID":"55632dca94c8","Image":"1919d446eafa","Labels":"maintainer=feedback@checkmk.com","LocalVolumes":"0","Mounts":"","Names":"stoic_perlman","Networks":"bridge","Ports":"","RunningFor":"6',
            'days', 'ago","Size":"0B","Status":"Created"}'
        ],
        [
            '{"Command":"\\"/bin/bash\\"","CreatedAt":"2018-09-27', '19:06:07', '+0200',
            'CEST","ID":"85a41e54b0cc","Image":"centos:7","Labels":"org.label-schema.schema-version=1.0,org.label-schema.vendor=CentOS,org.label-schema.build-date=20180804,org.label-schema.license=GPLv2,org.label-schema.name=CentOS',
            'Base',
            'Image","LocalVolumes":"0","Mounts":"","Names":"vigorous_pare","Networks":"bridge","Ports":"","RunningFor":"2',
            'weeks', 'ago","Size":"0B","Status":"Exited', '(137)', '2', 'weeks', 'ago"}'
        ], []
    ]
}

EXPECTED_CONTAINERS3 = EXPECTED_CONTAINERS2

EXPECTED_IMAGES3 = {
    u'096300fde75d': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-13T06:15:30.34090448Z',
        u'CreatedSince': u'4 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'096300fde75d',
        u'RepoTags': ['checkmk/check-mk-enterprise:1.5.0-2018.09.13'],
        u'SharedSize': u'N/A',
        u'Size': u'818MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 817961530,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0-2018.09.13'
        },
        'amount_containers': 0
    },
    u'0983f5184ce7': {
        u'Containers': u'N/A',
        u'Created': u'2018-10-12T14:07:29.732808446Z',
        u'CreatedSince': u'3 days ago',
        u'Digest': u'<none>',
        u'Id': u'0983f5184ce7',
        u'SharedSize': u'N/A',
        u'Size': u'312MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 312404556,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com'
        },
        'amount_containers': 1
    },
    u'2e89feac7533': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-13T06:27:42.955259674Z',
        u'CreatedSince': u'4 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'2e89feac7533',
        u'SharedSize': u'N/A',
        u'Size': u'831MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 831418094,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'2018.09.13'
        },
        'amount_containers': 0
    },
    u'44a5d6d15272': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-14T10:45:50.232853938Z',
        u'CreatedSince': u'4 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'44a5d6d15272',
        u'SharedSize': u'N/A',
        u'Size': u'818MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 817965472,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0-2018.09.14'
        },
        'amount_containers': 0
    },
    u'44e19a16bde1': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-04T21:21:34.566479261Z',
        u'CreatedSince': u'5 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'44e19a16bde1',
        u'SharedSize': u'N/A',
        u'Size': u'55.3MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 55270217,
        'amount_containers': 0
    },
    u'485933207afd': {
        u'Containers': u'N/A',
        u'Created': u'2018-10-12T14:12:03.009245184Z',
        u'CreatedSince': u'3 days ago',
        u'Digest': u'<none>',
        u'Id': u'485933207afd',
        u'SharedSize': u'N/A',
        u'Size': u'818MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 817562729,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        'amount_containers': 0
    },
    u'4a77be28f8e5': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-28T21:54:16.702903575Z',
        u'CreatedSince': u'2 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'4a77be28f8e5',
        u'SharedSize': u'N/A',
        u'Size': u'752MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 751885817,
        'Labels': {
            u'maintainer': u'feedback@checkmk.com',
            u'org.opencontainers.image.description': u'Check_MK is a leading tool for Infrastructure & Application Monitoring',
            u'org.opencontainers.image.source': u'https://github.com/tribe29/checkmk',
            u'org.opencontainers.image.title': u'Checkmk',
            u'org.opencontainers.image.url': u'https://checkmk.com/',
            u'org.opencontainers.image.vendor': u'tribe29 GmbH',
            u'org.opencontainers.image.version': u'1.5.0p5'
        },
        'amount_containers': 1
    },
    u'5182e96772bf': {
        u'Containers': u'N/A',
        u'Created': u'2018-08-06T19:21:48.235227329Z',
        u'CreatedSince': u'2 months ago',
        u'Digest': u'<none>',
        u'Id': u'5182e96772bf',
        u'SharedSize': u'N/A',
        u'Size': u'200MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 199723824,
        'Labels': {
            u'org.label-schema.build-date': u'20180804',
            u'org.label-schema.license': u'GPLv2',
            u'org.label-schema.name': u'CentOS Base Image',
            u'org.label-schema.schema-version': u'1.0',
            u'org.label-schema.vendor': u'CentOS'
        },
        'amount_containers': 1
    },
    u'6143303a8e14': {
        u'Containers': u'N/A',
        u'Created': u'2018-09-10T15:36:25.80531779Z',
        u'CreatedSince': u'5 weeks ago',
        u'Digest': u'<none>',
        u'Id': u'6143303a8e14',
        u'SharedSize': u'N/A',
        u'Size': u'3.64MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 3644760,
        'amount_containers': 0
    },
    u'6c97da45403a': {
        u'Containers': u'N/A',
        u'Created': u'2018-10-12T09:12:15.613593451Z',
        u'CreatedSince': u'4 days ago',
        u'Digest': u'<none>',
        u'Id': u'6c97da45403a',
        u'SharedSize': u'N/A',
        u'Size': u'200MB',
        u'UniqueSize': u'N/A',
        u'VirtualSize': 199723824,
        'Labels': {
            u'org.label-schema.build-date': u'20180804',
            u'org.label-schema.license': u'GPLv2',
            u'org.label-schema.name': u'CentOS Base Image',
            u'org.label-schema.schema-version': u'1.0',
            u'org.label-schema.vendor': u'CentOS'
        },
        'amount_containers': 0
    },
}


@pytest.mark.parametrize("subsections,ex_img,ex_cont", [
    (SUBSECTIONS1, EXPECTED_IMAGES1, EXPECTED_CONTAINERS1),
    (SUBSECTIONS2, EXPECTED_IMAGES2, EXPECTED_CONTAINERS2),
    (SUBSECTIONS3, EXPECTED_IMAGES3, EXPECTED_CONTAINERS3),
])
def test_parse_legacy_docker_node_images(subsections, ex_img, ex_cont):
    def assert_contains(dic, key, value):
        assert isinstance(dic, dict)
        assert key in dic, "key missing in output: %r" % key
        if isinstance(value, dict):
            for recurse_key, recurse_value in value.iteritems():
                assert_contains(dic[key], recurse_key, recurse_value)
        else:
            assert dic[key] == value, "expected: %r, got: %r" % (value, dic[key])

    parsed = parse_legacy_docker_node_images(subsections)  # pylint: disable=undefined-variable
    assert_contains(parsed, "images", ex_img)
    assert_contains(parsed, "containers", ex_cont)

    for image in parsed["images"].itervalues():
        for key, type_ in REQUIRED_IMAGE_KEYS:
            assert key in image
            assert isinstance(image[key], type_)

    for container in parsed["containers"].itervalues():
        for key, type_ in REQUIRED_CONTAINER_KEYS:
            assert key in container
            assert isinstance(container[key], type_)
