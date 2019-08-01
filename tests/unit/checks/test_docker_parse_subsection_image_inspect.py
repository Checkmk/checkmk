import pytest
import os
import re

pytestmark = pytest.mark.checks

exec (open(os.path.join(os.path.dirname(__file__), '../../../checks/legacy_docker.include')).read())

regex = re.compile


@pytest.mark.parametrize('indata,outdata', [
    ([], {}),
    ([
        ['['],
        ['    {'],
        [
            '        "Id": "sha256:4a77be28f8e54a4e6a8ecd8cfbd1963463d1e7ac719990206ced057af41e9957",'
        ],
        ['        "RepoTags": ['],
        ['            "checkmk/check-mk-raw:1.5.0p5"'],
        ['        ],'],
        ['        "RepoDigests": ['],
        [
            '            "checkmk/check-mk-raw@sha256:afcf4a9f843809598ccb9ddd11a6c415ef465e31969141304e9be57c3e53b438"'
        ],
        ['        ],'],
        ['        "Parent": "",'],
        ['        "Comment": "",'],
        ['        "Created": "2018-09-28T21:54:16.702903575Z",'],
        [
            '        "Container": "c26cf21a0abb0d087ac0d3ff42fa9865fa06778e2e4e021e2c4f34d6a52d373a",'
        ],
        ['        "ContainerConfig": {'],
        ['            "Hostname": "c26cf21a0abb",'],
        ['            "Domainname": "",'],
        ['            "User": "",'],
        ['            "AttachStdin": false,'],
        ['            "AttachStdout": false,'],
        ['            "AttachStderr": false,'],
        ['            "ExposedPorts": {'],
        ['                "5000/tcp": {},'],
        ['                "6557/tcp": {}'],
        ['            },'],
        ['            "Tty": false,'],
        ['            "OpenStdin": false,'],
        ['            "StdinOnce": false,'],
        ['            "Env": ['],
        ['                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['                "CMK_SITE_ID=cmk",'],
        ['                "CMK_LIVESTATUS_TCP=",'],
        ['                "CMK_PASSWORD=",'],
        ['                "MAIL_RELAY_HOST="'],
        ['            ],'],
        ['            "Cmd": ['],
        ['                "/bin/sh",'],
        ['                "-c",'],
        ['                "#(nop) ",'],
        ['               "ENTRYPOINT [\\"/docker-entrypoint.sh\\"]"'],
        ['            ],'],
        ['            "Healthcheck": {'],
        ['                "Test": ['],
        ['                    "CMD-SHELL",'],
        ['                    "omd status || exit 1"'],
        ['                ],'],
        ['                "Interval": 60000000000,'],
        ['                "Timeout": 5000000000'],
        ['            },'],
        ['            "ArgsEscaped": true,'],
        [
            '            "Image": "sha256:377f530526c6b6a0c6f9a609662d323a8beb33fdcc7004507ca09fa958884389",'
        ],
        ['            "Volumes": null,'],
        ['            "WorkingDir": "",'],
        ['            "Entrypoint": ['],
        ['                "/docker-entrypoint.sh"'],
        ['            ],'],
        ['            "OnBuild": null,'],
        ['            "Labels": {'],
        ['                "maintainer": "feedback@checkmk.com",'],
        [
            '                "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",'
        ],
        [
            '                "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",'
        ],
        ['                "org.opencontainers.image.title": "Checkmk",'],
        ['                "org.opencontainers.image.url": "https://checkmk.com/",'],
        ['                "org.opencontainers.image.vendor": "tribe29 GmbH",'],
        ['                "org.opencontainers.image.version": "1.5.0p5"'],
        ['            }'],
        ['        },'],
        ['        "DockerVersion": "18.06.1-ce",'],
        ['        "Author": "",'],
        ['        "Config": {'],
        ['            "Hostname": "",'],
        ['            "Domainname": "",'],
        ['            "User": "",'],
        ['            "AttachStdin": false,'],
        ['            "AttachStdout": false,'],
        ['            "AttachStderr": false,'],
        ['            "ExposedPorts": {'],
        ['                "5000/tcp": {},'],
        ['                "6557/tcp": {}'],
        ['            },'],
        ['            "Tty": false,'],
        ['            "OpenStdin": false,'],
        ['            "StdinOnce": false,'],
        ['            "Env": ['],
        ['                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['                "CMK_SITE_ID=cmk",'],
        ['                "CMK_LIVESTATUS_TCP=",'],
        ['                "CMK_PASSWORD=",'],
        ['                "MAIL_RELAY_HOST="'],
        ['            ],'],
        ['            "Cmd": null,'],
        ['            "Healthcheck": {'],
        ['                "Test": ['],
        ['                    "CMD-SHELL",'],
        ['                    "omd status || exit 1"'],
        ['                ],'],
        ['                "Interval": 60000000000,'],
        ['                "Timeout": 5000000000'],
        ['            },'],
        ['            "ArgsEscaped": true,'],
        [
            '            "Image": "sha256:377f530526c6b6a0c6f9a609662d323a8beb33fdcc7004507ca09fa958884389",'
        ],
        ['            "Volumes": null,'],
        ['            "WorkingDir": "",'],
        ['            "Entrypoint": ['],
        ['                "/docker-entrypoint.sh"'],
        ['            ],'],
        ['            "OnBuild": null,'],
        ['            "Labels": {'],
        ['                "maintainer": "feedback@checkmk.com",'],
        [
            '                "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",'
        ],
        [
            '                "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",'
        ],
        ['                "org.opencontainers.image.title": "Checkmk",'],
        ['                "org.opencontainers.image.url": "https://checkmk.com/",'],
        ['                "org.opencontainers.image.vendor": "tribe29 GmbH",'],
        ['                "org.opencontainers.image.version": "1.5.0p5"'],
        ['            }'],
        ['        },'],
        ['        "Architecture": "amd64",'],
        ['        "Os": "linux",'],
        ['        "Size": 751885817,'],
        ['        "VirtualSize": 751885817,'],
        ['        "GraphDriver": {'],
        ['            "Data": {'],
        [
            '                "LowerDir": "/var/lib/docker/overlay2/fcf841c2678358530a6e4c54a4b470c92b6e405501dec99d9f9017c4b719d692/diff:/var/lib/docker/overlay2/5d02afa6ae5354db5d085e7be03f166c370035b088cc8e33971ab97735f398fc/diff:/var/lib/docker/overlay2/782b7f29b434ee2da2e132920e6a337fd2ee715cdfc5e008121eca655b797de0/diff:/var/lib/docker/overlay2/e1354760894f7abc1488535001152c7785baa9406ab38701e0672dff6780cd98/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '                "MergedDir": "/var/lib/docker/overlay2/bbc63882ef27a4f49162c3f70ddc991f23b452b31846d03a8103e7c2691de42d/merged",'
        ],
        [
            '                "UpperDir": "/var/lib/docker/overlay2/bbc63882ef27a4f49162c3f70ddc991f23b452b31846d03a8103e7c2691de42d/diff",'
        ],
        [
            '                "WorkDir": "/var/lib/docker/overlay2/bbc63882ef27a4f49162c3f70ddc991f23b452b31846d03a8103e7c2691de42d/work"'
        ],
        ['            },'],
        ['            "Name": "overlay2"'],
        ['        },'],
        ['        "RootFS": {'],
        ['            "Type": "layers",'],
        ['            "Layers": ['],
        [
            '                "sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'
        ],
        [
            '                "sha256:a710e8ce658e07af2a635abf0e8d5bd80b036da50f9482c0b7258a640e875ca0",'
        ],
        [
            '                "sha256:03d65c16e5071740137f5135f448886feb99b30ab1556d3b9876db635ac16f9b",'
        ],
        [
            '                "sha256:d237d9e48fb17af4ff6cc6894f166024dbbb3103ad02e1b6b45504785448c263",'
        ],
        [
            '                "sha256:69f1282c62f326711f026b07689648028e17d58c06604429d8c55409f301980c",'
        ],
        [
            '                "sha256:4460e53d99d49e52302d5a107102b0f93ad5a670e9a8d5e7bd96b75af9866b58"'
        ],
        ['            ]'],
        ['        },'],
        ['        "Metadata": {'],
        ['            "LastTagTime": "0001-01-01T00:00:00Z"'],
        ['        }'],
        ['    },'],
        ['    {'],
        [
            '        "Id": "sha256:f4bfbb70768f233f1adca8e9e7333695a263773c2663a97732519f3e0eed87b7",'
        ],
        ['        "RepoTags": ['],
        ['            "docker-tests/check-mk-enterprise-master-1.5.0p3:latest"'],
        ['        ],'],
        ['        "RepoDigests": [],'],
        [
            '        "Parent": "sha256:a46c70fafb97acdc4643257a07e2290d96ab4242fdfe11e0ae318bcc3c5325f1",'
        ],
        ['        "Comment": "",'],
        ['        "Created": "2018-09-17T07:47:56.00338337Z",'],
        [
            '        "Container": "bbe8233e326b8302e2f4a2dcdc3e7bd4c95eb0a86ecdbb23c7aa996754bfbec0",'
        ],
        ['        "ContainerConfig": {'],
        ['            "Hostname": "bbe8233e326b",'],
        ['            "Domainname": "",'],
        ['            "User": "",'],
        ['            "AttachStdin": false,'],
        ['            "AttachStdout": false,'],
        ['            "AttachStderr": false,'],
        ['            "ExposedPorts": {'],
        ['                "5000/tcp": {},'],
        ['                "6557/tcp": {}'],
        ['            },'],
        ['            "Tty": false,'],
        ['            "OpenStdin": false,'],
        ['            "StdinOnce": false,'],
        ['            "Env": ['],
        ['                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['                "CMK_SITE_ID=cmk",'],
        ['                "CMK_LIVESTATUS_TCP=",'],
        ['                "CMK_PASSWORD=",'],
        ['                "MAIL_RELAY_HOST="'],
        ['            ],'],
        ['            "Cmd": ['],
        ['                "/bin/sh",'],
        ['                "-c",'],
        ['                "#(nop) ",'],
        ['                "ENTRYPOINT [\\"/docker-entrypoint.sh\\"]"'],
        ['            ],'],
        ['            "Healthcheck": {'],
        ['                "Test": ['],
        ['                    "CMD-SHELL",'],
        ['                    "omd status || exit 1"'],
        ['                ],'],
        ['                "Interval": 60000000000,'],
        ['                "Timeout": 5000000000'],
        ['            },'],
        ['            "ArgsEscaped": true,'],
        [
            '            "Image": "sha256:a46c70fafb97acdc4643257a07e2290d96ab4242fdfe11e0ae318bcc3c5325f1",'
        ],
        ['            "Volumes": null,'],
        ['            "WorkingDir": "",'],
        ['            "Entrypoint": ['],
        ['                "/docker-entrypoint.sh"'],
        ['            ],'],
        ['            "OnBuild": null,'],
        ['            "Labels": {'],
        ['                "maintainer": "feedback@checkmk.com",'],
        [
            '                "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",'
        ],
        [
            '                "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",'
        ],
        ['                "org.opencontainers.image.title": "Checkmk",'],
        ['                "org.opencontainers.image.url": "https://checkmk.com/",'],
        ['                "org.opencontainers.image.vendor": "tribe29 GmbH",'],
        ['                "org.opencontainers.image.version": "1.5.0p3"'],
        ['            }'],
        ['        },'],
        ['        "DockerVersion": "18.06.1-ce",'],
        ['        "Author": "",'],
        ['        "Config": {'],
        ['            "Hostname": "",'],
        ['            "Domainname": "",'],
        ['            "User": "",'],
        ['            "AttachStdin": false,'],
        ['            "AttachStdout": false,'],
        ['            "AttachStderr": false,'],
        ['            "ExposedPorts": {'],
        ['                "5000/tcp": {},'],
        ['                "6557/tcp": {}'],
        ['            },'],
        ['            "Tty": false,'],
        ['            "OpenStdin": false,'],
        ['            "StdinOnce": false,'],
        ['            "Env": ['],
        ['                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",'],
        ['                "CMK_SITE_ID=cmk",'],
        ['                "CMK_LIVESTATUS_TCP=",'],
        ['                "CMK_PASSWORD=",'],
        ['                "MAIL_RELAY_HOST="'],
        ['            ],'],
        ['            "Cmd": null,'],
        ['            "Healthcheck": {'],
        ['                "Test": ['],
        ['                    "CMD-SHELL",'],
        ['                    "omd status || exit 1"'],
        ['                ],'],
        ['                "Interval": 60000000000,'],
        ['                "Timeout": 5000000000'],
        ['            },'],
        ['            "ArgsEscaped": true,'],
        [
            '            "Image": "sha256:a46c70fafb97acdc4643257a07e2290d96ab4242fdfe11e0ae318bcc3c5325f1",'
        ],
        ['            "Volumes": null,'],
        ['            "WorkingDir": "",'],
        ['            "Entrypoint": ['],
        ['                "/docker-entrypoint.sh"'],
        ['            ],'],
        ['            "OnBuild": null,'],
        ['            "Labels": {'],
        ['                "maintainer": "feedback@checkmk.com",'],
        [
            '                "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",'
        ],
        [
            '                "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",'
        ],
        ['                "org.opencontainers.image.title": "Checkmk",'],
        ['                "org.opencontainers.image.url": "https://checkmk.com/",'],
        ['                "org.opencontainers.image.vendor": "tribe29 GmbH",'],
        ['                "org.opencontainers.image.version": "1.5.0p3"'],
        ['            }'],
        ['        },'],
        ['        "Architecture": "amd64",'],
        ['        "Os": "linux",'],
        ['        "Size": 817394362,'],
        ['        "VirtualSize": 817394362,'],
        ['        "GraphDriver": {'],
        ['            "Data": {'],
        [
            '                "LowerDir": "/var/lib/docker/overlay2/16035e64a82a6f55a5e0876f8b2fbe5c35ef1bb93aa5979aef0680c2488013ac/diff:/var/lib/docker/overlay2/08d4937752d7c6aebcfa07d8e1ba5d2e03f33a8c73cd23cbf5266933b9eebe71/diff:/var/lib/docker/overlay2/80100ea0ace33fdb5ad28be1789ed33c5c54642457317817ab81cad4444efe14/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",'
        ],
        [
            '                "MergedDir": "/var/lib/docker/overlay2/c03a524c9b03543dda1c33e6881037331fa4ce03ee649075f7265844035e1122/merged",'
        ],
        [
            '                "UpperDir": "/var/lib/docker/overlay2/c03a524c9b03543dda1c33e6881037331fa4ce03ee649075f7265844035e1122/diff",'
        ],
        [
            '                "WorkDir": "/var/lib/docker/overlay2/c03a524c9b03543dda1c33e6881037331fa4ce03ee649075f7265844035e1122/work"'
        ],
        ['            },'],
        ['            "Name": "overlay2"'],
        ['        },'],
        ['        "RootFS": {'],
        ['            "Type": "layers",'],
        ['            "Layers": ['],
        [
            '                "sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",'
        ],
        [
            '                "sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'
        ],
        [
            '                "sha256:4a1700eadae95c7651520e26f35b95333a6d57466fcc48ed71b6f2ee60bf1578",'
        ],
        [
            '                "sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",'
        ],
        [
            '                "sha256:31d940abd6efd3f4fc1fbf26814fc34f909ecb3046c7bd1d850f7fb2cc97f52a",'
        ],
        [
            '                "sha256:f666cd41893b4a04d00407db5b8feb54fb1e4b86e75dc96d353ec0ecb9d9d55f"'
        ],
        ['            ]'],
        ['        },'],
        ['        "Metadata": {'],
        ['            "LastTagTime": "2018-09-17T09:47:56.078067461+02:00"'],
        ['        }'],
        ['    }'],
        [']'],
    ], {
        "4a77be28f8e5": {
            "Id": "sha256:4a77be28f8e54a4e6a8ecd8cfbd1963463d1e7ac719990206ced057af41e9957",
            "RepoTags": ["checkmk/check-mk-raw:1.5.0p5"],
            "RepoDigests": [
                "checkmk/check-mk-raw@sha256:afcf4a9f843809598ccb9ddd11a6c415ef465e31969141304e9be57c3e53b438"
            ],
            "Parent": "",
            "Comment": "",
            "Created": "2018-09-28T21:54:16.702903575Z",
            "Container": "c26cf21a0abb0d087ac0d3ff42fa9865fa06778e2e4e021e2c4f34d6a52d373a",
            "ContainerConfig": {
                "Hostname": "c26cf21a0abb",
                "Domainname": "",
                "User": "",
                "AttachStdin": False,
                "AttachStdout": False,
                "AttachStderr": False,
                "ExposedPorts": {
                    "5000/tcp": {},
                    "6557/tcp": {}
                },
                "Tty": False,
                "OpenStdin": False,
                "StdinOnce": False,
                "Env": [
                    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "CMK_SITE_ID=cmk", "CMK_LIVESTATUS_TCP=", "CMK_PASSWORD=", "MAIL_RELAY_HOST="
                ],
                "Cmd": ["/bin/sh", "-c", "#(nop) ", "ENTRYPOINT [\"/docker-entrypoint.sh\"]"],
                "Healthcheck": {
                    "Test": ["CMD-SHELL", "omd status || exit 1"],
                    "Interval": 60000000000,
                    "Timeout": 5000000000
                },
                "ArgsEscaped": True,
                "Image": "sha256:377f530526c6b6a0c6f9a609662d323a8beb33fdcc7004507ca09fa958884389",
                "Volumes": None,
                "WorkingDir": "",
                "Entrypoint": ["/docker-entrypoint.sh"],
                "OnBuild": None,
                "Labels": {
                    "maintainer": "feedback@checkmk.com",
                    "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
                    "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
                    "org.opencontainers.image.title": "Checkmk",
                    "org.opencontainers.image.url": "https://checkmk.com/",
                    "org.opencontainers.image.vendor": "tribe29 GmbH",
                    "org.opencontainers.image.version": "1.5.0p5"
                }
            },
            "DockerVersion": "18.06.1-ce",
            "Author": "",
            "Config": {
                "Hostname": "",
                "Domainname": "",
                "User": "",
                "AttachStdin": False,
                "AttachStdout": False,
                "AttachStderr": False,
                "ExposedPorts": {
                    "5000/tcp": {},
                    "6557/tcp": {}
                },
                "Tty": False,
                "OpenStdin": False,
                "StdinOnce": False,
                "Env": [
                    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "CMK_SITE_ID=cmk", "CMK_LIVESTATUS_TCP=", "CMK_PASSWORD=", "MAIL_RELAY_HOST="
                ],
                "Cmd": None,
                "Healthcheck": {
                    "Test": ["CMD-SHELL", "omd status || exit 1"],
                    "Interval": 60000000000,
                    "Timeout": 5000000000
                },
                "ArgsEscaped": True,
                "Image": "sha256:377f530526c6b6a0c6f9a609662d323a8beb33fdcc7004507ca09fa958884389",
                "Volumes": None,
                "WorkingDir": "",
                "Entrypoint": ["/docker-entrypoint.sh"],
                "OnBuild": None,
                "Labels": {
                    "maintainer": "feedback@checkmk.com",
                    "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
                    "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
                    "org.opencontainers.image.title": "Checkmk",
                    "org.opencontainers.image.url": "https://checkmk.com/",
                    "org.opencontainers.image.vendor": "tribe29 GmbH",
                    "org.opencontainers.image.version": "1.5.0p5"
                }
            },
            "Architecture": "amd64",
            "Os": "linux",
            "Size": 751885817,
            "VirtualSize": 751885817,
            "GraphDriver": {
                "Data": {
                    "LowerDir": "/var/lib/docker/overlay2/fcf841c2678358530a6e4c54a4b470c92b6e405501dec99d9f9017c4b719d692/diff:/var/lib/docker/overlay2/5d02afa6ae5354db5d085e7be03f166c370035b088cc8e33971ab97735f398fc/diff:/var/lib/docker/overlay2/782b7f29b434ee2da2e132920e6a337fd2ee715cdfc5e008121eca655b797de0/diff:/var/lib/docker/overlay2/e1354760894f7abc1488535001152c7785baa9406ab38701e0672dff6780cd98/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",
                    "MergedDir": "/var/lib/docker/overlay2/bbc63882ef27a4f49162c3f70ddc991f23b452b31846d03a8103e7c2691de42d/merged",
                    "UpperDir": "/var/lib/docker/overlay2/bbc63882ef27a4f49162c3f70ddc991f23b452b31846d03a8103e7c2691de42d/diff",
                    "WorkDir": "/var/lib/docker/overlay2/bbc63882ef27a4f49162c3f70ddc991f23b452b31846d03a8103e7c2691de42d/work"
                },
                "Name": "overlay2"
            },
            "RootFS": {
                "Type": "layers",
                "Layers": [
                    "sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",
                    "sha256:a710e8ce658e07af2a635abf0e8d5bd80b036da50f9482c0b7258a640e875ca0",
                    "sha256:03d65c16e5071740137f5135f448886feb99b30ab1556d3b9876db635ac16f9b",
                    "sha256:d237d9e48fb17af4ff6cc6894f166024dbbb3103ad02e1b6b45504785448c263",
                    "sha256:69f1282c62f326711f026b07689648028e17d58c06604429d8c55409f301980c",
                    "sha256:4460e53d99d49e52302d5a107102b0f93ad5a670e9a8d5e7bd96b75af9866b58"
                ]
            },
            "Metadata": {
                "LastTagTime": "0001-01-01T00:00:00Z"
            }
        },
        "f4bfbb70768f": {
            "Id": "sha256:f4bfbb70768f233f1adca8e9e7333695a263773c2663a97732519f3e0eed87b7",
            "RepoTags": ["docker-tests/check-mk-enterprise-master-1.5.0p3:latest"],
            "RepoDigests": [],
            "Parent": "sha256:a46c70fafb97acdc4643257a07e2290d96ab4242fdfe11e0ae318bcc3c5325f1",
            "Comment": "",
            "Created": "2018-09-17T07:47:56.00338337Z",
            "Container": "bbe8233e326b8302e2f4a2dcdc3e7bd4c95eb0a86ecdbb23c7aa996754bfbec0",
            "ContainerConfig": {
                "Hostname": "bbe8233e326b",
                "Domainname": "",
                "User": "",
                "AttachStdin": False,
                "AttachStdout": False,
                "AttachStderr": False,
                "ExposedPorts": {
                    "5000/tcp": {},
                    "6557/tcp": {}
                },
                "Tty": False,
                "OpenStdin": False,
                "StdinOnce": False,
                "Env": [
                    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "CMK_SITE_ID=cmk", "CMK_LIVESTATUS_TCP=", "CMK_PASSWORD=", "MAIL_RELAY_HOST="
                ],
                "Cmd": ["/bin/sh", "-c", "#(nop) ", "ENTRYPOINT [\"/docker-entrypoint.sh\"]"],
                "Healthcheck": {
                    "Test": ["CMD-SHELL", "omd status || exit 1"],
                    "Interval": 60000000000,
                    "Timeout": 5000000000
                },
                "ArgsEscaped": True,
                "Image": "sha256:a46c70fafb97acdc4643257a07e2290d96ab4242fdfe11e0ae318bcc3c5325f1",
                "Volumes": None,
                "WorkingDir": "",
                "Entrypoint": ["/docker-entrypoint.sh"],
                "OnBuild": None,
                "Labels": {
                    "maintainer": "feedback@checkmk.com",
                    "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
                    "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
                    "org.opencontainers.image.title": "Checkmk",
                    "org.opencontainers.image.url": "https://checkmk.com/",
                    "org.opencontainers.image.vendor": "tribe29 GmbH",
                    "org.opencontainers.image.version": "1.5.0p3"
                }
            },
            "DockerVersion": "18.06.1-ce",
            "Author": "",
            "Config": {
                "Hostname": "",
                "Domainname": "",
                "User": "",
                "AttachStdin": False,
                "AttachStdout": False,
                "AttachStderr": False,
                "ExposedPorts": {
                    "5000/tcp": {},
                    "6557/tcp": {}
                },
                "Tty": False,
                "OpenStdin": False,
                "StdinOnce": False,
                "Env": [
                    "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "CMK_SITE_ID=cmk", "CMK_LIVESTATUS_TCP=", "CMK_PASSWORD=", "MAIL_RELAY_HOST="
                ],
                "Cmd": None,
                "Healthcheck": {
                    "Test": ["CMD-SHELL", "omd status || exit 1"],
                    "Interval": 60000000000,
                    "Timeout": 5000000000
                },
                "ArgsEscaped": True,
                "Image": "sha256:a46c70fafb97acdc4643257a07e2290d96ab4242fdfe11e0ae318bcc3c5325f1",
                "Volumes": None,
                "WorkingDir": "",
                "Entrypoint": ["/docker-entrypoint.sh"],
                "OnBuild": None,
                "Labels": {
                    "maintainer": "feedback@checkmk.com",
                    "org.opencontainers.image.description": "Check_MK is a leading tool for Infrastructure & Application Monitoring",
                    "org.opencontainers.image.source": "https://github.com/tribe29/checkmk",
                    "org.opencontainers.image.title": "Checkmk",
                    "org.opencontainers.image.url": "https://checkmk.com/",
                    "org.opencontainers.image.vendor": "tribe29 GmbH",
                    "org.opencontainers.image.version": "1.5.0p3"
                }
            },
            "Architecture": "amd64",
            "Os": "linux",
            "Size": 817394362,
            "VirtualSize": 817394362,
            "GraphDriver": {
                "Data": {
                    "LowerDir": "/var/lib/docker/overlay2/16035e64a82a6f55a5e0876f8b2fbe5c35ef1bb93aa5979aef0680c2488013ac/diff:/var/lib/docker/overlay2/08d4937752d7c6aebcfa07d8e1ba5d2e03f33a8c73cd23cbf5266933b9eebe71/diff:/var/lib/docker/overlay2/80100ea0ace33fdb5ad28be1789ed33c5c54642457317817ab81cad4444efe14/diff:/var/lib/docker/overlay2/d4d216c6b7427ebd78b6aa7b94ad78478535107a99a7e426735395d47db9d62f/diff:/var/lib/docker/overlay2/2a04ea231bbb83c5286fb6f1f23f59f48bcb44d0f556f6ebe0b0ec8f80b66808/diff",
                    "MergedDir": "/var/lib/docker/overlay2/c03a524c9b03543dda1c33e6881037331fa4ce03ee649075f7265844035e1122/merged",
                    "UpperDir": "/var/lib/docker/overlay2/c03a524c9b03543dda1c33e6881037331fa4ce03ee649075f7265844035e1122/diff",
                    "WorkDir": "/var/lib/docker/overlay2/c03a524c9b03543dda1c33e6881037331fa4ce03ee649075f7265844035e1122/work"
                },
                "Name": "overlay2"
            },
            "RootFS": {
                "Type": "layers",
                "Layers": [
                    "sha256:8b15606a9e3e430cb7ba739fde2fbb3734a19f8a59a825ffa877f9be49059817",
                    "sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",
                    "sha256:4a1700eadae95c7651520e26f35b95333a6d57466fcc48ed71b6f2ee60bf1578",
                    "sha256:67a401d014298693b23b091b2fa5f61aab98e680334df74058c310c27a874c4d",
                    "sha256:31d940abd6efd3f4fc1fbf26814fc34f909ecb3046c7bd1d850f7fb2cc97f52a",
                    "sha256:f666cd41893b4a04d00407db5b8feb54fb1e4b86e75dc96d353ec0ecb9d9d55f"
                ]
            },
            "Metadata": {
                "LastTagTime": "2018-09-17T09:47:56.078067461+02:00"
            }
        },
    }),
])
def test_parse_docker_image_inspect(indata, outdata):
    parsed = parse_legacy_docker_subsection_image_inspect(indata)
    assert parsed == outdata, "expected: %r, got %r" % (outdata, parsed)
