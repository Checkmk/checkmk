import pytest
import os
import re

pytestmark = pytest.mark.checks

exec (open(os.path.join(os.path.dirname(__file__), '../../../checks/legacy_docker.include')).read())

regex = re.compile


@pytest.mark.parametrize('indata,outdata', [
    ([], {}),
    ([
        ['TYPE           TOTAL  ACTIVE   SIZE       RECLAIMABLE'],
        ['Images         7      6        2.076 GB   936.9 MB (45%)'],
        ['Containers     22     0        2.298 GB   2.298 GB (100%)'],
        ['Local Volumes  5      5        304 B      0 B (0%)'],
    ], {
        "images": {
            "type": "Images",
            "count": 7,
            "active": 6,
            "size": 2076000000,
            "reclaimable": 936900000
        },
        "containers": {
            "type": "Containers",
            "count": 22,
            "active": 0,
            "size": 2298000000,
            "reclaimable": 2298000000
        },
        "local volumes": {
            "type": "Local Volumes",
            "count": 5,
            "active": 5,
            "size": 304,
            "reclaimable": 0
        }
    }),
    ([
        [
            'TYPE                TOTAL               ACTIVE              SIZE                RECLAIMABLE'
        ],
        [
            'Images              15                  2                   9.57GB              8.674GB (90%)'
        ],
        [
            'Containers          2                   1                   1.226GB             1.224GB (99%)'
        ],
        ['Local Volumes       1                   1                   9.323MB             0B (0%)'],
        ['Build Cache                                                 0B                  0B'],
    ], {
        "images": {
            "type": "Images",
            "count": 15,
            "active": 2,
            "size": 9570000000,
            "reclaimable": 8674000000
        },
        "containers": {
            "type": "Containers",
            "count": 2,
            "active": 1,
            "size": 1226000000,
            "reclaimable": 1224000000
        },
        "local volumes": {
            "type": "Local Volumes",
            "count": 1,
            "active": 1,
            "size": 9323000,
            "reclaimable": 0
        },
        "build cache": {
            "type": "Build Cache",
            "count": 0,
            "active": 0,
            "size": 0,
            "reclaimable": 0
        },
    }),
    ([
        [
            'TYPE                TOTAL               ACTIVE              SIZE                RECLAIMABLE'
        ],
        [
            'Images              15                  2                   9.57GB              8.674GB (90%)'
        ],
        [
            'Containers          2                   1                   1.226GB             1.224GB (99%)'
        ],
        ['Local Volumes       1                   1                   9.323MB             0B (0%)'],
        ['Build Cache         0                   0                   0B                  0B'],
    ], {
        "images": {
            "type": "Images",
            "count": 15,
            "active": 2,
            "size": 9570000000,
            "reclaimable": 8674000000
        },
        "containers": {
            "type": "Containers",
            "count": 2,
            "active": 1,
            "size": 1226000000,
            "reclaimable": 1224000000
        },
        "local volumes": {
            "type": "Local Volumes",
            "count": 1,
            "active": 1,
            "size": 9323000,
            "reclaimable": 0
        },
        "build cache": {
            "type": "Build Cache",
            "count": 0,
            "active": 0,
            "size": 0,
            "reclaimable": 0
        },
    }),
])
def test_parse_legacy_docker_system_df(indata, outdata):
    parsed = parse_legacy_docker_system_df(indata)  # pylint: disable=undefined-variable
    assert parsed == outdata, "expected: %r, got %r" % (outdata, parsed)
