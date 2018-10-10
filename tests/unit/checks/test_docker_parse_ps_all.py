# *--encoding: UTF-8--*
import pytest
import os
import re

pytestmark = pytest.mark.checks

execfile(os.path.join(os.path.dirname(__file__), '../../../checks/docker.include'))

regex = re.compile

@pytest.mark.parametrize('indata,outdata', [
    ([], {}),
    ([
      ['CONTAINER ID   IMAGE                   COMMAND                              CREATED             STATUS                      PORTS    NAMES'],
      ['7f3cc936aa7b   rhel7                   "bash"                               3 months ago        Exited (0) 3 months ago              thirsty_torvalds'],
      ['a0271671c515   rhscl/redis-32-rhel7    "container-entrypoint bash"          4 months ago        Exited (130) 4 months ago            heuristic_bassi'],
      ['1ff46b4d4d75   rhscl/redis-32-rhel7    "container-entrypoint run-redis"     4 months ago        Exited (0) 4 months ago              serene_brattain'],
     ], {
         '7f3cc936aa7b': {
            "ID": '7f3cc936aa7b',
            "Image": 'rhel7',
            "Repository": 'rhel7',
            "Tag": 'latest',
            "Command": '"bash"',
            "CreatedAt": '3 months ago',
            "Status": 'Exited (0) 3 months ago',
            "Ports": '',
            "Names": 'thirsty_torvalds'},
         'a0271671c515': {
             "ID": 'a0271671c515',
             "Image": 'rhscl/redis-32-rhel7',
             "Repository": 'rhscl/redis-32-rhel7',
             "Tag": 'latest',
             "Command": '"container-entrypoint bash"',
             "CreatedAt": '4 months ago',
             "Status": 'Exited (130) 4 months ago',
             "Ports": '',
             "Names": 'heuristic_bassi'},
         '1ff46b4d4d75': {
             "ID": '1ff46b4d4d75',
             "Image": 'rhscl/redis-32-rhel7',
             "Repository": 'rhscl/redis-32-rhel7',
             "Tag": 'latest',
             "Command": '"container-entrypoint run-redis"',
             "CreatedAt": '4 months ago',
             "Status": 'Exited (0) 4 months ago',
             "Ports": '',
             "Names": 'serene_brattain'},
          }),
    ([
      ['CONTAINER ID        IMAGE                          COMMAND                  CREATED             STATUS                     PORTS                              NAMES'],
      ['b58b7b9d1cde        checkmk/check-mk-raw:1.5.0p5   "/docker-entrypoint.…"   10 days ago         Up 5 hours (healthy)       6557/tcp, 0.0.0.0:8080->5000/tcp   monitoring'],
      ['85a41e54b0cc        centos:7                       "/bin/bash"              11 days ago         Exited (137) 11 days ago                                      vigorous_pare'],
     ], {
         'b58b7b9d1cde': {
             "ID": 'b58b7b9d1cde',
             "Image": 'checkmk/check-mk-raw:1.5.0p5',
             "Repository": 'checkmk/check-mk-raw',
             "Tag": '1.5.0p5',
             "Command": '"/docker-entrypoint.…"',
             "CreatedAt": '10 days ago',
             "Status": 'Up 5 hours (healthy)',
             "Ports": '6557/tcp, 0.0.0.0:8080->5000/tcp',
             "Names": 'monitoring'},
         '85a41e54b0cc': {
             "ID": '85a41e54b0cc', 
             "Image": 'centos:7',
             "Repository": 'centos',
             "Tag": '7',
             "Command": '"/bin/bash"',
             "CreatedAt": '11 days ago',
             "Status": 'Exited (137) 11 days ago',
             "Ports": '',
             "Names": 'vigorous_pare'}
         })
])
def test_parse_docker_ps_all(indata, outdata):
    parsed = parse_docker_ps_all(indata)
    assert parsed == outdata, "expected: %r, got %r" % (outdata, parsed)
