import pytest
import os
import re

pytestmark = pytest.mark.checks

execfile(os.path.join(os.path.dirname(__file__), '../../../checks/legacy_docker.include'))

regex = re.compile

@pytest.mark.parametrize('indata,outdata', [
    ([], {}),
    ([
      ['TYPE           TOTAL  ACTIVE   SIZE       RECLAIMABLE'],
      ['Images         7      6        2.076 GB   936.9 MB (45%)'],
      ['Containers     22     0        2.298 GB   2.298 GB (100%)'],
      ['Local Volumes  5      5        304 B      0 B (0%)'],
      ], {"images": {
              "Type": "Images",
              "TotalCount": 7,
              "Active": 6,
              "Size": 2076000000,
              "Reclaimable": 936900000},
          "containers": {
              "Type": "Containers",
              "TotalCount": 22,
              "Active": 0,
              "Size": 2298000000,
              "Reclaimable": 2298000000},
          "local volumes": {
              "Type": "Local Volumes",
              "TotalCount": 5,
              "Active": 5,
              "Size": 304,
              "Reclaimable": 0}
          }),
    ([
      ['TYPE                TOTAL               ACTIVE              SIZE                RECLAIMABLE'],
      ['Images              15                  2                   9.57GB              8.674GB (90%)'],
      ['Containers          2                   1                   1.226GB             1.224GB (99%)'],
      ['Local Volumes       1                   1                   9.323MB             0B (0%)'],
      ['Build Cache                                                 0B                  0B'],
      ], {"images": {
              "Type": "Images",
              "TotalCount": 15,
              "Active": 2,
              "Size": 9570000000,
              "Reclaimable": 8674000000},
          "containers": {
              "Type": "Containers",
              "TotalCount": 2,
              "Active": 1,
              "Size": 1226000000,
              "Reclaimable": 1224000000},
          "local volumes": {
              "Type": "Local Volumes",
              "TotalCount": 1,
              "Active": 1,
              "Size": 9323000,
              "Reclaimable": 0},
          "build cache": {
              "Type": "Build Cache",
              "TotalCount": 0,
              "Active": 0,
              "Size": 0,
              "Reclaimable": 0},
          }),
    ([
      ['TYPE                TOTAL               ACTIVE              SIZE                RECLAIMABLE'],
      ['Images              15                  2                   9.57GB              8.674GB (90%)'],
      ['Containers          2                   1                   1.226GB             1.224GB (99%)'],
      ['Local Volumes       1                   1                   9.323MB             0B (0%)'],
      ['Build Cache         0                   0                   0B                  0B'],
      ], {"images": {
              "Type": "Images",
              "TotalCount": 15,
              "Active": 2,
              "Size": 9570000000,
              "Reclaimable": 8674000000},
          "containers": {
              "Type": "Containers",
              "TotalCount": 2,
              "Active": 1,
              "Size": 1226000000,
              "Reclaimable": 1224000000},
          "local volumes": {
              "Type": "Local Volumes",
              "TotalCount": 1,
              "Active": 1,
              "Size": 9323000,
              "Reclaimable": 0},
          "build cache": {
              "Type": "Build Cache",
              "TotalCount": 0,
              "Active": 0,
              "Size": 0,
              "Reclaimable": 0},
          }),
])
def test_parse_docker_system_df(indata, outdata):
    parsed = parse_docker_system_df(indata)
    assert parsed == outdata, "expected: %r, got %r" % (outdata, parsed)
