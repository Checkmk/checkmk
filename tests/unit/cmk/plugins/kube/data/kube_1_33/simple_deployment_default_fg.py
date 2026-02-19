#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A simple deployment created in Kind by the cluster collector Helm chart.
# No extra Feature Gates are enabled.

DATA = {
    "apiVersion": "apps/v1",
    "kind": "Deployment",
    "metadata": {
        "annotations": {
            "deployment.kubernetes.io/revision": "1",
            "meta.helm.sh/release-name": "myrelease",
            "meta.helm.sh/release-namespace": "checkmk-monitoring",
        },
        "creationTimestamp": "2026-02-20T09:03:55Z",
        "generation": 1,
        "labels": {
            "app": "myrelease-checkmk-cluster-collector",
            "app.kubernetes.io/instance": "myrelease",
            "app.kubernetes.io/managed-by": "Helm",
            "app.kubernetes.io/name": "checkmk",
            "app.kubernetes.io/version": "1.9.0",
            "component": "myrelease-checkmk-cluster-collector",
            "helm.sh/chart": "checkmk-1.9.0",
        },
        "name": "myrelease-checkmk-cluster-collector",
        "namespace": "checkmk-monitoring",
        "resourceVersion": "630",
        "uid": "742413a1-2e0c-4af5-bc33-f785847b40c5",
    },
    "spec": {
        "progressDeadlineSeconds": 600,
        "replicas": 1,
        "revisionHistoryLimit": 10,
        "selector": {
            "matchLabels": {
                "app": "myrelease-checkmk-cluster-collector",
                "app.kubernetes.io/instance": "myrelease",
                "app.kubernetes.io/name": "checkmk",
                "component": "myrelease-checkmk-cluster-collector",
            }
        },
        "strategy": {
            "rollingUpdate": {"maxSurge": "25%", "maxUnavailable": "25%"},
            "type": "RollingUpdate",
        },
        "template": {
            "metadata": {
                "creationTimestamp": None,
                "labels": {
                    "app": "myrelease-checkmk-cluster-collector",
                    "app.kubernetes.io/instance": "myrelease",
                    "app.kubernetes.io/name": "checkmk",
                    "component": "myrelease-checkmk-cluster-collector",
                },
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
                        "volumeMounts": [{"mountPath": "/mnt/tmp", "name": "tmp"}],
                    }
                ],
                "dnsPolicy": "ClusterFirst",
                "restartPolicy": "Always",
                "schedulerName": "default-scheduler",
                "securityContext": {},
                "serviceAccount": "myrelease-checkmk-cluster-collector",
                "serviceAccountName": "myrelease-checkmk-cluster-collector",
                "terminationGracePeriodSeconds": 30,
                "volumes": [{"emptyDir": {"medium": "Memory"}, "name": "tmp"}],
            },
        },
    },
    "status": {
        "availableReplicas": 1,
        "conditions": [
            {
                "lastTransitionTime": "2026-02-20T09:04:07Z",
                "lastUpdateTime": "2026-02-20T09:04:07Z",
                "message": "Deployment has minimum availability.",
                "reason": "MinimumReplicasAvailable",
                "status": "True",
                "type": "Available",
            },
            {
                "lastTransitionTime": "2026-02-20T09:03:55Z",
                "lastUpdateTime": "2026-02-20T09:04:07Z",
                "message": 'ReplicaSet "myrelease-checkmk-cluster-collector-86d456fb9c" has successfully progressed.',
                "reason": "NewReplicaSetAvailable",
                "status": "True",
                "type": "Progressing",
            },
        ],
        "observedGeneration": 1,
        "readyReplicas": 1,
        "replicas": 1,
        "updatedReplicas": 1,
    },
}
