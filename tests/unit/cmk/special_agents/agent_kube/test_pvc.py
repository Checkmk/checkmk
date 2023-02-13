#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pydantic_factories import ModelFactory

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import section


class AttachedVolumeFactory(ModelFactory):
    __model__ = section.AttachedVolume


class PVCMetadataFactory(ModelFactory):
    __model__ = section.PersistentVolumeClaimMetaData


class PersistentVolumeClaimFactory(ModelFactory):
    __model__ = section.PersistentVolumeClaim


class PersistentVolumeFactory(ModelFactory):
    __model__ = section.PersistentVolume


def test_group_serialized_volumes_by_namespace():
    namespace_name = "ns1"
    volumes = AttachedVolumeFactory.batch(size=3, namespace=namespace_name)
    namespaced_grouped_volumes = agent.group_serialized_volumes_by_namespace(iter(volumes))

    assert namespaced_grouped_volumes == {
        namespace_name: {v.persistent_volume_claim: v for v in volumes}
    }


def test_group_parsed_pvcs_by_namespace():
    namespace_name = "ns1"
    pvc = PersistentVolumeClaimFactory.build(
        metadata=PVCMetadataFactory.build(namespace=namespace_name)
    )
    grouped_pvc = agent.group_parsed_pvcs_by_namespace([pvc])
    assert grouped_pvc == {namespace_name: {pvc.metadata.name: pvc}}


def test_create_pvc_sections():
    """Test the creation of the PVC & PV related sections

    This test also highlights how the PVC & PV objects are related to each other
    (Yes this is based majorly on the same linking mechanism used by the Kubernetes API)
    """
    attached_pvc_name = "pvc1"
    attached_pv_name = "pv1"

    api_pvc = PersistentVolumeClaimFactory.build(
        metadata=PVCMetadataFactory.build(name=attached_pvc_name),
        volume_name=attached_pv_name,
    )
    api_pv = PersistentVolumeFactory.build(name=attached_pv_name)
    volume = AttachedVolumeFactory.build()

    sections = list(
        agent.create_pvc_sections(
            piggyback_name="default",
            attached_pvc_names=[attached_pvc_name],
            api_pvcs={api_pvc.metadata.name: api_pvc},
            api_pvs={api_pv.name: api_pv},
            attached_volumes={attached_pvc_name: volume},
        )
    )

    assert [s.section_name for s in sections] == [
        "kube_pvc_v1",
        "kube_pvc_pvs_v1",
        "kube_pvc_volumes_v1",
    ]
