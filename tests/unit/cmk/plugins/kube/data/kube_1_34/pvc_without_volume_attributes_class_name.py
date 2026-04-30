#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

DATA = {
    "apiVersion": "v1",
    "kind": "PersistentVolumeClaim",
    "metadata": {
        "annotations": {
            "kubectl.kubernetes.io/last-applied-configuration": '{"apiVersion":"v1","kind":"PersistentVolumeClaim","metadata":{"annotations":{},"name":"test-pvc","namespace":"checkmk-monitoring"},"spec":{"accessModes":["ReadWriteOnce"],"resources":{"requests":{"storage":"1Gi"}},"storageClassName":"manual"}}\n',
            "pv.kubernetes.io/bind-completed": "yes",
            "pv.kubernetes.io/bound-by-controller": "yes",
        },
        "creationTimestamp": "2026-03-19T17:34:36Z",
        "finalizers": ["kubernetes.io/pvc-protection"],
        "name": "test-pvc",
        "namespace": "checkmk-monitoring",
        "resourceVersion": "44039",
        "uid": "4188ef93-b59f-48f1-98ff-052dec929d94",
    },
    "spec": {
        "accessModes": ["ReadWriteOnce"],
        "resources": {"requests": {"storage": "1Gi"}},
        "storageClassName": "manual",
        "volumeMode": "Filesystem",
        "volumeName": "test-local-pv",
    },
    "status": {"accessModes": ["ReadWriteOnce"], "capacity": {"storage": "1Gi"}, "phase": "Bound"},
}
