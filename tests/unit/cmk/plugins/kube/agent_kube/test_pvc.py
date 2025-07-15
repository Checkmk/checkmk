#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.plugins.kube.agent_handlers.persistent_volume_claim_handler import (
    create_pvc_sections,
    group_parsed_pvcs_by_namespace,
    group_serialized_volumes_by_namespace,
)
from cmk.plugins.kube.schemata import api, section
from tests.unit.cmk.plugins.kube.agent_kube import factory


class SectionPVCMetadataFactory(ModelFactory):
    __model__ = section.PersistentVolumeClaimMetaData


class SectionPersistentVolumeClaimFactory(ModelFactory):
    __model__ = section.PersistentVolumeClaim


class SectionPersistentVolumeFactory(ModelFactory):
    __model__ = section.PersistentVolume


class AttachedVolumeFactory(ModelFactory):
    __model__ = section.AttachedVolume


def test_group_serialized_volumes_by_namespace():
    namespace_name = api.NamespaceName("ns1")
    volumes = AttachedVolumeFactory.batch(size=3, namespace=namespace_name)
    namespaced_grouped_volumes = group_serialized_volumes_by_namespace(iter(volumes))

    assert namespaced_grouped_volumes == {
        namespace_name: {v.persistent_volume_claim: v for v in volumes}
    }


def test_group_parsed_pvcs_by_namespace():
    namespace_name = api.NamespaceName("ns1")
    api_pvc = factory.PersistentVolumeClaimFactory.build(
        metadata=factory.MetaDataFactory.build(namespace=namespace_name, factory_use_construct=True)
    )
    grouped_pvc = group_parsed_pvcs_by_namespace([api_pvc])
    assert len(grouped_pvc) == 1
    assert (namespace_group := grouped_pvc.get(namespace_name)) is not None
    assert len(namespace_group) == 1
    assert (pvc := namespace_group.get(api_pvc.metadata.name)) is not None
    assert pvc.volume_name == api_pvc.spec.volume_name


def test_create_pvc_sections():
    """Test the creation of the PVC & PV related sections

    This test also highlights how the PVC & PV objects are related to each other
    (Yes this is based majorly on the same linking mechanism used by the Kubernetes API)
    """
    attached_pvc_name = "pvc1"
    attached_pv_name = "pv1"

    api_pvc = SectionPersistentVolumeClaimFactory.build(
        metadata=SectionPVCMetadataFactory.build(name=attached_pvc_name),
        volume_name=attached_pv_name,
    )
    api_pv = SectionPersistentVolumeFactory.build(name=attached_pv_name)
    volume = AttachedVolumeFactory.build()

    sections = list(
        create_pvc_sections(
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
