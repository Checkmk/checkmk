import pytest
import os
import re

pytestmark = pytest.mark.checks

execfile(os.path.join(os.path.dirname(__file__), '../../../checks/docker.include'))

regex = re.compile

@pytest.mark.parametrize('indata,outdata', [
    ([], {}),
    ([
      ['REPOSITORY                                               TAG                 IMAGE ID            CREATED             SIZE'],
      ['docker.io/hello-world                                    latest              4ab4c602aa5e        3 weeks ago         1.84 kB'],
      ['registry.access.redhat.com/rhel6                         latest              02482caaf480        2 months ago        200 MB'],
      ['registry.access.redhat.com/jboss-eap-7/eap71-openshift   latest              b7bd8964cbf5        5 months ago        741 MB'],
     ], {"4ab4c602aa5e": {
              "Repository": 'docker.io/hello-world',
              "Tag": 'latest',
              "ID": '4ab4c602aa5e',
              "CreatedAt": '3 weeks ago',
              "VirtualSize": 1840},
          "02482caaf480": {
              "Repository": 'registry.access.redhat.com/rhel6',
              "Tag": 'latest',
              "ID": '02482caaf480',
              "CreatedAt": '2 months ago',
              "VirtualSize": 200000000},
          "b7bd8964cbf5": {
              "Repository": 'registry.access.redhat.com/jboss-eap-7/eap71-openshift',
              "Tag": 'latest',
              "ID": 'b7bd8964cbf5',
              "CreatedAt": '5 months ago',
              "VirtualSize": 741000000},
          }),
    ([
      ['REPOSITORY                                           TAG                 IMAGE ID            CREATED             SIZE'],
      ['checkmk/check-mk-raw                                 1.5.0p5             4a77be28f8e5        10 days ago         752MB'],
      ['docker-tests/check-mk-enterprise-master-1.5.0p3      latest              f4bfbb70768f        3 weeks ago         817MB'],
     ], {"4a77be28f8e5": {
              "Repository": 'checkmk/check-mk-raw',
              "Tag": '1.5.0p5',
              "ID": '4a77be28f8e5',
              "CreatedAt": '10 days ago',
              "VirtualSize": 752000000},
         "f4bfbb70768f": {
             "Repository": 'docker-tests/check-mk-enterprise-master-1.5.0p3',
             "Tag": 'latest',
             "ID": 'f4bfbb70768f',
             "CreatedAt": '3 weeks ago',
             "VirtualSize": 817000000},
         }),
      ])
def test_parse_docker_images(indata, outdata):
    parsed = parse_docker_images(indata)
    assert parsed == outdata, "expected: %r, got %r" % (outdata, parsed)
