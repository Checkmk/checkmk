#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

DATA = {
    "apiVersion": "v1",
    "kind": "PersistentVolumeClaim",
    "metadata": {
        "annotations": {
            "kubectl.kubernetes.io/last-applied-configuration": '{"apiVersion":"v1","kind":"PersistentVolumeClaim","metadata":{"annotations":{},"name":"test-pvc","namespace":"checkmk-monitoring"},"spec":{"accessModes":["ReadWriteOnce"],"resources":{"requests":{"storage":"1Gi"}},"storageClassName":"csi-hostpath-sc","volumeAttributesClassName":"silver"}}\n',
            "pv.kubernetes.io/bind-completed": "yes",
            "pv.kubernetes.io/bound-by-controller": "yes",
            "volume.beta.kubernetes.io/storage-provisioner": "hostpath.csi.k8s.io",
            "volume.kubernetes.io/storage-provisioner": "hostpath.csi.k8s.io",
        },
        "creationTimestamp": "2026-03-19T15:51:47Z",
        "finalizers": ["kubernetes.io/pvc-protection"],
        "name": "test-pvc",
        "namespace": "checkmk-monitoring",
        "resourceVersion": "33687",
        "uid": "b1e5294c-7b7e-4682-8ead-afd9f8b09deb",
    },
    "spec": {
        "accessModes": ["ReadWriteOnce"],
        "resources": {"requests": {"storage": "1Gi"}},
        "storageClassName": "manual",
        "volumeAttributesClassName": "silver",
        "volumeMode": "Filesystem",
        "volumeName": "test-local-pv",
    },
    "status": {
        "accessModes": ["ReadWriteOnce"],
        "capacity": {"storage": "1Gi"},
        "currentVolumeAttributesClassName": "silver",
        "phase": "Bound",
    },
}
