#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

DATA = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "generateName": "checkmk-cluster-collector-84bf9d765d-",
        "generation": 1,
        "labels": {
            "app": "checkmk-cluster-collector",
            "app.kubernetes.io/instance": "checkmk",
            "app.kubernetes.io/name": "checkmk",
            "component": "checkmk-cluster-collector",
            "pod-template-hash": "84bf9d765d",
        },
        "name": "checkmk-cluster-collector-84bf9d765d-lqlrf",
        "namespace": "checkmk-monitoring",
        "ownerReferences": [
            {
                "apiVersion": "apps/v1",
                "blockOwnerDeletion": True,
                "controller": True,
                "kind": "ReplicaSet",
                "name": "checkmk-cluster-collector-84bf9d765d",
                "uid": "ca536034-e2fd-4ef1-a062-94eb62df88f6",
            }
        ],
        "resourceVersion": "44075",
        "uid": "d9a48207-cf39-4e72-b6b5-4d355d0a9491",
    },
    "spec": {
        "containers": [
            {
                "args": [
                    "--log-level=warning",
                    "--address=0.0.0.0",
                    "--cache-maxsize=50000",
                    "--reader-whitelist=checkmk-monitoring:checkmk-checkmk",
                    "--writer-whitelist=checkmk-monitoring:checkmk-node-collector-container-metrics,checkmk-monitoring:checkmk-node-collector-machine-sections",
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
                    {"mountPath": "/tmp", "name": "tmp"},
                    {
                        "mountPath": "/var/run/secrets/kubernetes.io/serviceaccount",
                        "name": "kube-api-access-pf9dl",
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
        "restartPolicy": "Always",
        "schedulerName": "default-scheduler",
        "securityContext": {},
        "serviceAccount": "checkmk-cluster-collector",
        "serviceAccountName": "checkmk-cluster-collector",
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
            {"name": "mypvc", "persistentVolumeClaim": {"claimName": "test-pvc"}},
            {"emptyDir": {"medium": "Memory"}, "name": "tmp"},
            {
                "name": "kube-api-access-pf9dl",
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
                "lastTransitionTime": "2026-03-19T17:34:39Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "PodReadyToStartContainers",
            },
            {
                "lastProbeTime": None,
                "lastTransitionTime": "2026-03-19T17:34:38Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "Initialized",
            },
            {
                "lastProbeTime": None,
                "lastTransitionTime": "2026-03-19T17:34:50Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "Ready",
            },
            {
                "lastProbeTime": None,
                "lastTransitionTime": "2026-03-19T17:34:50Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "ContainersReady",
            },
            {
                "lastProbeTime": None,
                "lastTransitionTime": "2026-03-19T17:34:38Z",
                "observedGeneration": 1,
                "status": "True",
                "type": "PodScheduled",
            },
        ],
        "containerStatuses": [
            {
                "allocatedResources": {"cpu": "150m", "memory": "200Mi"},
                "containerID": "containerd://8c8a8357e604b48a682d66977de16031fcfccd934f4dc354373e23ffa6b805a5",
                "image": "docker.io/checkmk/kubernetes-collector:1.9.0",
                "imageID": "docker.io/checkmk/kubernetes-collector@sha256:7baa14ccd1b4820432c4a3ae1f79b9ec78ebcf29211c130215a2e2cee4d722d4",
                "lastState": {},
                "name": "cluster-collector",
                "ready": True,
                "resources": {"requests": {"cpu": "150m", "memory": "200Mi"}},
                "restartCount": 0,
                "started": True,
                "state": {"running": {"startedAt": "2026-03-19T17:34:38Z"}},
                "user": {"linux": {"gid": 10001, "supplementalGroups": [10001], "uid": 10001}},
                "volumeMounts": [
                    {"mountPath": "/tmp", "name": "tmp"},
                    {
                        "mountPath": "/var/run/secrets/kubernetes.io/serviceaccount",
                        "name": "kube-api-access-pf9dl",
                        "readOnly": True,
                        "recursiveReadOnly": "Disabled",
                    },
                ],
            }
        ],
        "hostIP": "172.18.0.2",
        "hostIPs": [{"ip": "172.18.0.2"}],
        "observedGeneration": 1,
        "phase": "Running",
        "podIP": "10.244.1.14",
        "podIPs": [{"ip": "10.244.1.14"}],
        "qosClass": "Burstable",
        "startTime": "2026-03-19T17:34:38Z",
    },
}
