#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

DATA = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "creationTimestamp": "2026-03-31T01:27:31Z",
        "generateName": "myrelease-checkmk-cluster-collector-574957fbbb-",
        "generation": 1,
        "labels": {
            "app": "myrelease-checkmk-cluster-collector",
            "app.kubernetes.io/instance": "myrelease",
            "app.kubernetes.io/name": "checkmk",
            "component": "myrelease-checkmk-cluster-collector",
            "pod-template-hash": "574957fbbb",
        },
        "name": "myrelease-checkmk-cluster-collector-574957fbbb-crrts",
        "namespace": "checkmk-monitoring",
        "ownerReferences": [
            {
                "apiVersion": "apps/v1",
                "blockOwnerDeletion": True,
                "controller": True,
                "kind": "ReplicaSet",
                "name": "myrelease-checkmk-cluster-collector-574957fbbb",
                "uid": "37356af0-5c44-4a47-96db-1307eb2ee9ad",
            }
        ],
        "resourceVersion": "566232",
        "uid": "29de3ffa-7479-4c93-8486-88386fb6bdc5",
    },
    "spec": {
        "containers": [
            {
                "args": [
                    "--log-level=warning",
                    "--address=0.0.0.0",
                    "--cache-maxsize=50000",
                    "--reader-whitelist=checkmk-monitoring:myrelease-checkmk-checkmk",
                    "--writer-whitelist=checkmk-monitoring:myrelease-checkmk-node-collector-container-metrics,checkmk-monitoring:myrelease-checkmk-node-collector-machine-sections",
                ],
                "command": ["/usr/local/bin/checkmk-cluster-collector"],
                "env": [
                    {
                        "name": "NODE_NAME",
                        "valueFrom": {
                            "fieldRef": {"apiVersion": "v1", "fieldPath": "spec.nodeName"}
                        },
                    }
                ],
                "image": "checkmk/kubernetes-collector:1.9.0",
                "imagePullPolicy": "IfNotPresent",
                "livenessProbe": {
                    "failureThreshold": 3,
                    "httpGet": {
                        "httpHeaders": [{"name": "status", "value": "available"}],
                        "path": "/health",
                        "port": "api",
                        "scheme": "HTTP",
                    },
                    "initialDelaySeconds": 3,
                    "periodSeconds": 10,
                    "successThreshold": 1,
                    "timeoutSeconds": 2,
                },
                "name": "cluster-collector",
                "ports": [{"containerPort": 10050, "name": "api", "protocol": "TCP"}],
                "readinessProbe": {
                    "failureThreshold": 3,
                    "httpGet": {"path": "/health", "port": "api", "scheme": "HTTP"},
                    "initialDelaySeconds": 3,
                    "periodSeconds": 10,
                    "successThreshold": 1,
                    "timeoutSeconds": 2,
                },
                "resources": {"requests": {"cpu": "150m", "memory": "200Mi"}},
                "securityContext": {
                    "allowPrivilegeEscalation": False,
                    "capabilities": {"drop": ["ALL"]},
                    "privileged": False,
                    "readOnlyRootFilesystem": True,
                    "runAsGroup": 10001,
                    "runAsNonRoot": True,
                    "runAsUser": 10001,
                    "seccompProfile": {"type": "RuntimeDefault"},
                },
                "terminationMessagePath": "/dev/termination-log",
                "terminationMessagePolicy": "File",
                "volumeMounts": [
                    {"mountPath": "/mnt/tmp", "name": "tmp"},
                    {
                        "mountPath": "/var/run/secrets/kubernetes.io/serviceaccount",
                        "name": "kube-api-access-t2b5t",
                        "readOnly": True,
                    },
                ],
            }
        ],
        "dnsPolicy": "ClusterFirst",
        "enableServiceLinks": True,
        "nodeName": "kind-worker",
        "preemptionPolicy": "PreemptLowerPriority",
        "priority": 0,
        "resources": {
            "limits": {"cpu": "1", "memory": "1Gi"},
            "requests": {"cpu": "500m", "memory": "512Mi"},
        },
        "restartPolicy": "Always",
        "schedulerName": "default-scheduler",
        "securityContext": {},
        "serviceAccount": "myrelease-checkmk-cluster-collector",
        "serviceAccountName": "myrelease-checkmk-cluster-collector",
        "terminationGracePeriodSeconds": 30,
        "tolerations": [
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/not-ready",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
            {
                "effect": "NoExecute",
                "key": "node.kubernetes.io/unreachable",
                "operator": "Exists",
                "tolerationSeconds": 300,
            },
        ],
        "volumes": [
            {"emptyDir": {"medium": "Memory"}, "name": "tmp"},
            {
                "name": "kube-api-access-t2b5t",
                "projected": {
                    "defaultMode": 420,
                    "sources": [
                        {"serviceAccountToken": {"expirationSeconds": 3607, "path": "token"}},
                        {
                            "configMap": {
                                "items": [{"key": "ca.crt", "path": "ca.crt"}],
                                "name": "kube-root-ca.crt",
                            }
                        },
                        {
                            "downwardAPI": {
                                "items": [
                                    {
                                        "fieldRef": {
                                            "apiVersion": "v1",
                                            "fieldPath": "metadata.namespace",
                                        },
                                        "path": "namespace",
                                    }
                                ]
                            }
                        },
                    ],
                },
            },
        ],
    },
    "status": {
        "conditions": [
            {
                "lastProbeTime": None,
                "lastTransitionTime": "2026-03-31T01:27:32Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "PodReadyToStartContainers",
            },
            {
                "lastProbeTime": None,
                "lastTransitionTime": "2026-03-31T01:27:31Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "Initialized",
            },
            {
                "lastProbeTime": None,
                "lastTransitionTime": "2026-03-31T01:27:43Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "Ready",
            },
            {
                "lastProbeTime": None,
                "lastTransitionTime": "2026-03-31T01:27:43Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "ContainersReady",
            },
            {
                "lastProbeTime": None,
                "lastTransitionTime": "2026-03-31T01:27:31Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "PodScheduled",
            },
        ],
        "containerStatuses": [
            {
                "allocatedResources": {"cpu": "150m", "memory": "200Mi"},
                "containerID": "containerd://3f29ffdcc5ea42496c6655ffe1ab07723ef0e9107ddabc4d8d9043fbcac2dc3c",
                "image": "docker.io/checkmk/kubernetes-collector:1.9.0",
                "imageID": "docker.io/checkmk/kubernetes-collector@sha256:7baa14ccd1b4820432c4a3ae1f79b9ec78ebcf29211c130215a2e2cee4d722d4",
                "lastState": {},
                "name": "cluster-collector",
                "ready": True,
                "resources": {"requests": {"cpu": "150m", "memory": "200Mi"}},
                "restartCount": 0,
                "started": True,
                "state": {"running": {"startedAt": "2026-03-31T01:27:31Z"}},
                "user": {"linux": {"gid": 10001, "supplementalGroups": [10001], "uid": 10001}},
                "volumeMounts": [
                    {"mountPath": "/mnt/tmp", "name": "tmp"},
                    {
                        "mountPath": "/var/run/secrets/kubernetes.io/serviceaccount",
                        "name": "kube-api-access-t2b5t",
                        "readOnly": True,
                        "recursiveReadOnly": "Disabled",
                    },
                ],
            }
        ],
        "hostIP": "172.18.0.3",
        "hostIPs": [{"ip": "172.18.0.3"}],
        "observedGeneration": 1,
        "phase": "Running",
        "podIP": "10.244.1.8",
        "podIPs": [{"ip": "10.244.1.8"}],
        "qosClass": "Burstable",
        "startTime": "2026-03-31T01:27:31Z",
    },
}
