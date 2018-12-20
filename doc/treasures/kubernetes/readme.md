# Kubernetes Monitoring

Prometheus has become the standard software to monitor a kubernetes
cluster. It runs in its own container and (unfortunately) every application
that needs to use it ends up configuring its own instance of prometheus.

A very informative document on monitoring architecture for kubernetes can
be found here
<https://github.com/kubernetes/community/blob/master/contributors/design-proposals/instrumentation/monitoring_architecture.md>



## Check-MK monitoring idea for kubernetes

Because getting information out of a kubernetes cluster requires going
through a metrics pipeline we need to setup various components in the
system.

-   **Prometheus:** Scrapes the data from monitoring agent: Mainly the Kubelet,
    but services and applications can be setup to output
    metrics in the Prometheus protocol for targeted monitoring
-   **Prometheus Operator:** Manages Prometheus, just a piece of software that
    allows for a simpler and dynamical operation of Prometheus. It answers
    the needs of reloading configurations and restarting services under
    its management.
-   **Prometheus adapter:** Offers an API endpoint to query the metrics that
    have been scraped by Prometheus.
-   **Check\_MK special agent:** Queries the kubelet API or the adapter for metrics

![img](./monitoring-arch.png)

The usable yaml files to fire up a prometheus instance, managed by a
prometheus operator and that monitors the kubelet service are in
this directory, just apply it.

The adapter to expose custom metrix is also available.
I need to pack all this configuration into a check\_mk namespace.




### TODO Secure communication

All Prometheus related containers, pods, services and roles run inside the
kubernetes node. For the moment one abuses that confinement and allow for
insecure communication. This confinement does not mean any application
cannot eavesdrop the communication, it just mean from the outside one needs
a proxy to access it. The configuration to let internal communication
happen through TLS remains a part to deal with, those features are
supported, we need to deal with dealing with the certificates and other
nuances of encryption and authentication.




## Configuring Monitoring architecture

For the Check\_MK special agent to be able to query the Kubelet API for
metrics as the prometheus adapter we create a specific user for that goal.
Apply the rbac for check\_mk to get a service account with enough read
permissions.

    kubectl apply -f ~/git/check_mk/doc/treasures/kubernetes/check_mk_rbac.yaml


This should have created a Service Account, we can have a look at with:

    kubectl get serviceaccount check-mk -o yaml -n check-mk

    apiVersion: v1
    kind: ServiceAccount
    metadata:
      annotations:
        kubectl.kubernetes.io/last-applied-configuration: |
          {"apiVersion":"v1","kind":"ServiceAccount","metadata":{"annotations":{},"name":"check-mk","namespace":"check-mk"}}
      creationTimestamp: "2019-01-07T11:31:33Z"
      name: check-mk
      namespace: check-mk
      resourceVersion: "111238"
      selfLink: /api/v1/namespaces/check-mk/serviceaccounts/check-mk
      uid: c8cc6e72-126f-11e9-94b0-080027e0313a
    secrets:
    - name: check-mk-token-bc44j




### Get token

For Check\_MK to communicate to kubernetes we need to get the authentication
token. To first obtain the name of the token we use:

    kubectl get serviceaccount check-mk -o yaml  -n check-mk | grep "\- name:" | awk {'print $3'}

Which during this guide is:

    check-mk-token-bc44j

Replace it under `${token_name}` in the next command, which returns the token

    kubectl get secret ${token_name} -o yaml  -n check-mk | grep "token:" | awk {'print $2'} |  base64 --decode

    eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJjaGVjay1tayIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VjcmV0Lm5hbWUiOiJjaGVjay1tay10b2tlbi1iYzQ0aiIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJjaGVjay1tayIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImM4Y2M2ZTcyLTEyNmYtMTFlOS05NGIwLTA4MDAyN2UwMzEzYSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpjaGVjay1tazpjaGVjay1tayJ9.w1xNU0JoyQK8NMlpK2X7-ep4yjhOrjTXhwFmuHhvRX6MWSw4Gr72kQ2EFg8eDcZKPvAr7OYljducAcXvBTmvlhV9nWRsaZNBlWDsu3Jmw0YswQJlHs5VCLWk8_VbiLHKiRt8PX8zNoZBhUF1XzWYRJjKapPpcL4IAuQ57LsE_OgLf1Bfj9MbqfhSuIgoJ4AAn0UEslo5giQdLBRL1m6JMxeE1Xlv5Sl-Uc98DlwZFTwIdXj_X1iOqRkepA8DPFr4wjN3xPkKPiqP6l84x4Nwg6Z79Msq7FYG__XhlgVsRnCwUwfZwPKw0XqfncEtVYrUQPmP8EsrQ179Z_5bkPatmw

Copy this in your Check\_MK passwordstore. Then setup kubernetes as a data
source to use the special agent.




### Get certificate

This is the certificate to communicate from the exterior of kubernetes into
it. We need to give this certificate to Check\_MK for the special agent not
to complain about the communication.

    kubectl get secret ${token_name} -o yaml -n check-mk | grep "ca.crt:" | awk {'print $2'} |  base64 --decode

    -----BEGIN CERTIFICATE-----
    MIIC5zCCAc+gAwIBAgIBATANBgkqhkiG9w0BAQsFADAVMRMwEQYDVQQDEwptaW5p
    a3ViZUNBMB4XDTE4MTIxNjEzNDYzOFoXDTI4MTIxNDEzNDYzOFowFTETMBEGA1UE
    AxMKbWluaWt1YmVDQTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBALT5
    7EvR3ehKXx3LdztLTZllNXihDqeM2Px27FemBZ/LzVl0UQBqMAsNYHPHTs9KfrTw
    I0HGR5sp8dM+yOeg6EW8pFLjDpMyxf7Vxlfga2FHgW443fsQ+t6j6Vu780xMEvM5
    Kx/NNZSc7dVEyxD4jCZ+8iL0Rhd9sgiEvu8RjUlazIlltPUACAhNUwE1+oN5iBFo
    6wtDzkGkN6Yl2hEdGS/nUvEokiYV7as2WI++qepCmdmntzqK72+FW45rRLY4wsYT
    qCWRkZEzdnna6BKbeMigQ/vTF1LlbHj4XxsbM9SJiP8EKduN+TBz0ZWo7k618BK0
    030/bGtD5WWL5m2nocMCAwEAAaNCMEAwDgYDVR0PAQH/BAQDAgKkMB0GA1UdJQQW
    MBQGCCsGAQUFBwMCBggrBgEFBQcDATAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3
    DQEBCwUAA4IBAQCzWfneGoCou4jnCoB2bWzHC7rB3OVKFOAku+CjY/zYqFoiY9mI
    XX2ufCn6RSlsbWFZz1LR7hYzS07pi+pWddHOz66dXo3DlKEq0HpKF0u0d/P9C3uA
    JPJsxmunwYWhlVrbxfSpWaaiPZMAQD/Mc03CZrVl6FcNGcdxvHO/O0MoFMBZ1n74
    0jdh5jvVeQyxr1WWbIWqI6mj/OguyZMQkq3xGPrgwf4S1jKPWgOiESpdPPkruLUO
    H3/URbaENRRDpVQy1wh4DAjOg7Ex7tKujeXxuO/ihgzfL3f4+NX7tkSiQaudll3T
    Ik+23cGz8QC5aQ7HEjiuXzEW1a/lCS95WDsM
    -----END CERTIFICATE-----

For our Minikube node it looks like this.

    echo "${certificate}" | openssl x509 -text -noout

    Certificate:
        Data:
            Version: 3 (0x2)
            Serial Number: 1 (0x1)
        Signature Algorithm: sha256WithRSAEncryption
            Issuer: CN = minikubeCA
            Validity
                Not Before: Dec 16 13:46:38 2018 GMT
                Not After : Dec 14 13:46:38 2028 GMT
            Subject: CN = minikubeCA
            Subject Public Key Info:
                Public Key Algorithm: rsaEncryption
                    Public-Key: (2048 bit)
                    Modulus:
                        00:b4:f9:ec:4b:d1:dd:e8:4a:5f:1d:cb:77:3b:4b:
                        4d:99:65:35:78:a1:0e:a7:8c:d8:fc:76:ec:57:a6:
                        05:9f:cb:cd:59:74:51:00:6a:30:0b:0d:60:73:c7:
                        4e:cf:4a:7e:b4:f0:23:41:c6:47:9b:29:f1:d3:3e:
                        c8:e7:a0:e8:45:bc:a4:52:e3:0e:93:32:c5:fe:d5:
                        c6:57:e0:6b:61:47:81:6e:38:dd:fb:10:fa:de:a3:
                        e9:5b:bb:f3:4c:4c:12:f3:39:2b:1f:cd:35:94:9c:
                        ed:d5:44:cb:10:f8:8c:26:7e:f2:22:f4:46:17:7d:
                        b2:08:84:be:ef:11:8d:49:5a:cc:89:65:b4:f5:00:
                        08:08:4d:53:01:35:fa:83:79:88:11:68:eb:0b:43:
                        ce:41:a4:37:a6:25:da:11:1d:19:2f:e7:52:f1:28:
                        92:26:15:ed:ab:36:58:8f:be:a9:ea:42:99:d9:a7:
                        b7:3a:8a:ef:6f:85:5b:8e:6b:44:b6:38:c2:c6:13:
                        a8:25:91:91:91:33:76:79:da:e8:12:9b:78:c8:a0:
                        43:fb:d3:17:52:e5:6c:78:f8:5f:1b:1b:33:d4:89:
                        88:ff:04:29:db:8d:f9:30:73:d1:95:a8:ee:4e:b5:
                        f0:12:b4:d3:7d:3f:6c:6b:43:e5:65:8b:e6:6d:a7:
                        a1:c3
                    Exponent: 65537 (0x10001)
            X509v3 extensions:
                X509v3 Key Usage: critical
                    Digital Signature, Key Encipherment, Certificate Sign
                X509v3 Extended Key Usage:
                    TLS Web Client Authentication, TLS Web Server Authentication
                X509v3 Basic Constraints: critical
                    CA:TRUE
        Signature Algorithm: sha256WithRSAEncryption
             b3:59:f9:de:1a:80:a8:bb:88:e7:0a:80:76:6d:6c:c7:0b:ba:
             c1:dc:e5:4a:14:e0:24:bb:e0:a3:63:fc:d8:a8:5a:22:63:d9:
             88:5d:7d:ae:7c:29:fa:45:29:6c:6d:61:59:cf:52:d1:ee:16:
             33:4b:4e:e9:8b:ea:56:75:d1:ce:cf:ae:9d:5e:8d:c3:94:a1:
             2a:d0:7a:4a:17:4b:b4:77:f3:fd:0b:7b:80:24:f2:6c:c6:6b:
             a7:c1:85:a1:95:5a:db:c5:f4:a9:59:a6:a2:3d:93:00:40:3f:
             cc:73:4d:c2:66:b5:65:e8:57:0d:19:c7:71:bc:73:bf:3b:43:
             28:14:c0:59:d6:7e:f8:d2:37:61:e6:3b:d5:79:0c:b1:af:55:
             96:6c:85:aa:23:a9:a3:fc:e8:2e:c9:93:10:92:ad:f1:18:fa:
             e0:c1:fe:12:d6:32:8f:5a:03:a2:11:2a:5d:3c:f9:2b:b8:b5:
             0e:1f:7f:d4:45:b6:84:35:14:43:a5:54:32:d7:08:78:0c:08:
             ce:83:b1:31:ee:d2:ae:8d:e5:f1:b8:ef:e2:86:0c:df:2f:77:
             f8:f8:d5:fb:b6:44:a2:41:ab:9d:96:5d:d3:22:4f:b6:dd:c1:
             b3:f1:00:b9:69:0e:c7:12:38:ae:5f:31:16:d5:af:e5:09:2f:
             79:58:3b:0c




### Instantiate system

Apply the configuration files in doc/treasures/kubernetes/.

    kubectl apply -f doc/treasures/kubernetes/check_mk_rbac.yaml
    kubectl apply -f doc/treasures/kubernetes/prometheus-operator.yaml
    kubectl apply -f doc/treasures/kubernetes/sample-prometheus-instance.yaml
    kubectl apply -f doc/treasures/kubernetes/custom-metrics.yaml

The order is important, as each configuration installs the dependencies for
the following services, thus a wait for install period is necessary between
each command.
Verify that the prometheus service is running. It should be exposed at <http://clusterip:30999>
Verify that the configuration is correctly loaded and that the targets,
e.g. the kubelet system are being parsed. Also verify that the
custom-metrics api is offering data.

    kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/" | jq . | head -n 20

    {
      "kind": "APIResourceList",
      "apiVersion": "v1",
      "groupVersion": "custom.metrics.k8s.io/v1beta1",
      "resources": [
        {
          "name": "pods/spec_memory_limit_bytes",
          "singularName": "",
          "namespaced": true,
          "kind": "MetricValueList",
          "verbs": [
            "get"
          ]
        },
        {
          "name": "nodes/http_request_duration_microseconds_sum",
          "singularName": "",
          "namespaced": true,
          "kind": "MetricValueList",
          "verbs": [



# check\_mk special agent

To test the special agent from the terminal, use in the omd site environment

    share/check_mk/agents/special/agent_kubernetes --port 8443 --no-cert-check --token  "${token_secret}" $(minikube ip)
