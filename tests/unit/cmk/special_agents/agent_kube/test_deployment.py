#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.special_agents import agent_kube


def test_pod_deployment_controller_name(pod: agent_kube.Pod, deployment: agent_kube.Deployment):
    pod.add_controller(deployment)
    pod_info = pod.info()
    assert len(pod_info.controllers) == 1
    assert pod_info.controllers[0].name == deployment.name()
