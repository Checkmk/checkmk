#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

import cmk.plugins.jenkins.agent_based.jenkins_system_metrics as agent_module
from cmk.agent_based.v2 import Metric, Result, Service, State


@pytest.fixture(scope="module", name="section")
def _section() -> agent_module.Section:
    return agent_module.parse_jenkins_system_metrics(
        [
            [
                """
                {"version": "4.0.0", "gauges": {"jenkins.executor.count.value": {"value": 2}, "jenkins.executor.free.value": {"value": 2}, "jenkins.executor.in-use.value": {"value": 0}, "jenkins.health-check.count": {"value": 4}, "jenkins.health-check.inverse-score": {"value": 0.0}, "jenkins.health-check.score": {"value": 1.0}, "jenkins.job.averageDepth": {"value": 1.0}, "jenkins.job.count.value": {"value": 2}, "jenkins.node.count.value": {"value": 2}, "jenkins.node.offline.value": {"value": 1}, "jenkins.node.online.value": {"value": 1}, "jenkins.plugins.active": {"value": 88}, "jenkins.plugins.failed": {"value": 0}, "jenkins.plugins.inactive": {"value": 0}, "jenkins.plugins.withUpdate": {"value": 19}, "jenkins.project.count.value": {"value": 2}, "jenkins.project.disabled.count.value": {"value": 0}, "jenkins.project.enabled.count.value": {"value": 2}, "jenkins.queue.blocked.value": {"value": 3}, "jenkins.queue.buildable.value": {"value": 2}, "jenkins.queue.pending.value": {"value": 0}, "jenkins.queue.size.value": {"value": 5}, "jenkins.queue.stuck.value": {"value": 2}, "jenkins.versions.core": {"value": "2.426.3"}, "jenkins.versions.plugin.ant": {"value": "497.v94e7d9fffa_b_9"}, "jenkins.versions.plugin.antisamy-markup-formatter": {"value": "162.v0e6ec0fcfcf6"}, "jenkins.versions.plugin.apache-httpcomponents-client-4-api": {"value": "4.5.14-208.v438351942757"}, "jenkins.versions.plugin.asm-api": {"value": "9.7-33.v4d23ef79fcc8"}, "jenkins.versions.plugin.bootstrap5-api": {"value": "5.3.3-1"}, "jenkins.versions.plugin.bouncycastle-api": {"value": "2.30.1.77-225.v26ea_c9455fd9"}, "jenkins.versions.plugin.branch-api": {"value": "2.1152.v6f101e97dd77"}, "jenkins.versions.plugin.build-timeout": {"value": "1.32"}, "jenkins.versions.plugin.caffeine-api": {"value": "3.1.8-133.v17b_1ff2e0599"}, "jenkins.versions.plugin.checks-api": {"value": "2.2.0"}, "jenkins.versions.plugin.cloudbees-folder": {"value": "6.858.v898218f3609d"}, "jenkins.versions.plugin.commons-lang3-api": {"value": "3.13.0-62.v7d18e55f51e2"}, "jenkins.versions.plugin.commons-text-api": {"value": "1.11.0-109.vfe16c66636eb_"}, "jenkins.versions.plugin.credentials": {"value": "1337.v60b_d7b_c7b_c9f"}, "jenkins.versions.plugin.credentials-binding": {"value": "657.v2b_19db_7d6e6d"}, "jenkins.versions.plugin.display-url-api": {"value": "2.200.vb_9327d658781"}, "jenkins.versions.plugin.durable-task": {"value": "555.v6802fe0f0b_82"}, "jenkins.versions.plugin.echarts-api": {"value": "5.5.0-1"}, "jenkins.versions.plugin.email-ext": {"value": "2.105"}, "jenkins.versions.plugin.font-awesome-api": {"value": "6.5.1-3"}, "jenkins.versions.plugin.git": {"value": "5.2.1"}, "jenkins.versions.plugin.git-client": {"value": "4.7.0"}, "jenkins.versions.plugin.github": {"value": "1.38.0"}, "jenkins.versions.plugin.github-api": {"value": "1.318-461.v7a_c09c9fa_d63"}, "jenkins.versions.plugin.github-branch-source": {"value": "1787.v8b_8cd49a_f8f1"}, "jenkins.versions.plugin.gradle": {"value": "2.11"}, "jenkins.versions.plugin.gson-api": {"value": "2.10.1-15.v0d99f670e0a_7"}, "jenkins.versions.plugin.instance-identity": {"value": "185.v303dc7c645f9"}, "jenkins.versions.plugin.ionicons-api": {"value": "70.v2959a_b_74e3cf"}, "jenkins.versions.plugin.jackson2-api": {"value": "2.17.0-379.v02de8ec9f64c"}, "jenkins.versions.plugin.jakarta-activation-api": {"value": "2.1.3-1"}, "jenkins.versions.plugin.jakarta-mail-api": {"value": "2.1.3-1"}, "jenkins.versions.plugin.javax-activation-api": {"value": "1.2.0-6"}, "jenkins.versions.plugin.javax-mail-api": {"value": "1.6.2-9"}, "jenkins.versions.plugin.jaxb": {"value": "2.3.9-1"}, "jenkins.versions.plugin.jjwt-api": {"value": "0.11.5-112.ve82dfb_224b_a_d"}, "jenkins.versions.plugin.joda-time-api": {"value": "2.12.7-29.v5a_b_e3a_82269a_"}, "jenkins.versions.plugin.jquery3-api": {"value": "3.7.1-2"}, "jenkins.versions.plugin.json-api": {"value": "20240303-41.v94e11e6de726"}, "jenkins.versions.plugin.json-path-api": {"value": "2.9.0-58.v62e3e85b_a_655"}, "jenkins.versions.plugin.junit": {"value": "1265.v65b_14fa_f12f0"}, "jenkins.versions.plugin.ldap": {"value": "719.vcb_d039b_77d0d"}, "jenkins.versions.plugin.mailer": {"value": "470.vc91f60c5d8e2"}, "jenkins.versions.plugin.matrix-auth": {"value": "3.2.2"}, "jenkins.versions.plugin.matrix-project": {"value": "822.824.v14451b_c0fd42"}, "jenkins.versions.plugin.metrics": {"value": "4.2.21-451.vd51df8df52ec"}, "jenkins.versions.plugin.mina-sshd-api-common": {"value": "2.12.1-101.v85b_e08b_780dd"}, "jenkins.versions.plugin.mina-sshd-api-core": {"value": "2.12.1-101.v85b_e08b_780dd"}, "jenkins.versions.plugin.monitoring": {"value": "1.98.0"}, "jenkins.versions.plugin.okhttp-api": {"value": "4.11.0-172.vda_da_1feeb_c6e"}, "jenkins.versions.plugin.pam-auth": {"value": "1.10"}, "jenkins.versions.plugin.pipeline-build-step": {"value": "540.vb_e8849e1a_b_d8"}, "jenkins.versions.plugin.pipeline-github-lib": {"value": "42.v0739460cda_c4"}, "jenkins.versions.plugin.pipeline-graph-analysis": {"value": "216.vfd8b_ece330ca_"}, "jenkins.versions.plugin.pipeline-groovy-lib": {"value": "704.vc58b_8890a_384"}, "jenkins.versions.plugin.pipeline-input-step": {"value": "477.v339683a_8d55e"}, "jenkins.versions.plugin.pipeline-milestone-step": {"value": "119.vdfdc43fc3b_9a_"}, "jenkins.versions.plugin.pipeline-model-api": {"value": "2.2198.v41dd8ef6dd56"}, "jenkins.versions.plugin.pipeline-model-definition": {"value": "2.2198.v41dd8ef6dd56"}, "jenkins.versions.plugin.pipeline-model-extensions": {"value": "2.2198.v41dd8ef6dd56"}, "jenkins.versions.plugin.pipeline-rest-api": {"value": "2.34"}, "jenkins.versions.plugin.pipeline-stage-step": {"value": "312.v8cd10304c27a_"}, "jenkins.versions.plugin.pipeline-stage-tags-metadata": {"value": "2.2198.v41dd8ef6dd56"}, "jenkins.versions.plugin.pipeline-stage-view": {"value": "2.34"}, "jenkins.versions.plugin.plain-credentials": {"value": "179.vc5cb_98f6db_38"}, "jenkins.versions.plugin.plugin-util-api": {"value": "4.1.0"}, "jenkins.versions.plugin.resource-disposer": {"value": "0.23"}, "jenkins.versions.plugin.scm-api": {"value": "689.v237b_6d3a_ef7f"}, "jenkins.versions.plugin.script-security": {"value": "1335.vf07d9ce377a_e"}, "jenkins.versions.plugin.snakeyaml-api": {"value": "2.2-111.vc6598e30cc65"}, "jenkins.versions.plugin.ssh-credentials": {"value": "337.v395d2403ccd4"}, "jenkins.versions.plugin.ssh-slaves": {"value": "2.948.vb_8050d697fec"}, "jenkins.versions.plugin.structs": {"value": "337.v1b_04ea_4df7c8"}, "jenkins.versions.plugin.timestamper": {"value": "1.26"}, "jenkins.versions.plugin.token-macro": {"value": "400.v35420b_922dcb_"}, "jenkins.versions.plugin.trilead-api": {"value": "2.142.v748523a_76693"}, "jenkins.versions.plugin.variant": {"value": "60.v7290fc0eb_b_cd"}, "jenkins.versions.plugin.workflow-aggregator": {"value": "596.v8c21c963d92d"}, "jenkins.versions.plugin.workflow-api": {"value": "1291.v51fd2a_625da_7"}, "jenkins.versions.plugin.workflow-basic-steps": {"value": "1049.v257a_e6b_30fb_d"}, "jenkins.versions.plugin.workflow-cps": {"value": "3894.vd0f0248b_a_fc4"}, "jenkins.versions.plugin.workflow-durable-task-step": {"value": "1331.vc8c2fed35334"}, "jenkins.versions.plugin.workflow-job": {"value": "1385.vb_58b_86ea_fff1"}, "jenkins.versions.plugin.workflow-multibranch": {"value": "773.vc4fe1378f1d5"}, "jenkins.versions.plugin.workflow-scm-step": {"value": "427.v4ca_6512e7df1"}, "jenkins.versions.plugin.workflow-step-api": {"value": "657.v03b_e8115821b_"}, "jenkins.versions.plugin.workflow-support": {"value": "896.v175a_a_9c5b_78f"}, "jenkins.versions.plugin.ws-cleanup": {"value": "0.45"}, "system.cpu.load": {"value": 1.12890625}, "vm.blocked.count": {"value": 0}, "vm.class.loaded": {"value": 19768}, "vm.class.unloaded": {"value": 2325}, "vm.count": {"value": 38}, "vm.cpu.load": {"value": 0.014872904272579772}, "vm.daemon.count": {"value": 19}, "vm.deadlock.count": {"value": 0}, "vm.deadlocks": {"value": []}, "vm.file.descriptor.ratio": {"value": 0.00031185150146484375}, "vm.gc.G1-Old-Generation.count": {"value": 0}, "vm.gc.G1-Old-Generation.time": {"value": 0}, "vm.gc.G1-Young-Generation.count": {"value": 189}, "vm.gc.G1-Young-Generation.time": {"value": 1938}, "vm.memory.heap.committed": {"value": 419430400}, "vm.memory.heap.init": {"value": 524288000}, "vm.memory.heap.max": {"value": 8342470656}, "vm.memory.heap.usage": {"value": 0.028987583411644906}, "vm.memory.heap.used": {"value": 241828064}, "vm.memory.non-heap.committed": {"value": 192217088}, "vm.memory.non-heap.init": {"value": 7667712}, "vm.memory.non-heap.max": {"value": -1}, "vm.memory.non-heap.usage": {"value": 0.9267636392452268}, "vm.memory.non-heap.used": {"value": 178139808}, "vm.memory.pools.CodeHeap-\'non-nmethods\'.committed": {"value": 2752512}, "vm.memory.pools.CodeHeap-\'non-nmethods\'.init": {"value": 2555904}, "vm.memory.pools.CodeHeap-\'non-nmethods\'.max": {"value": 5840896}, "vm.memory.pools.CodeHeap-\'non-nmethods\'.usage": {"value": 0.4518758765778401}, "vm.memory.pools.CodeHeap-\'non-nmethods\'.used": {"value": 2639360}, "vm.memory.pools.CodeHeap-\'non-profiled-nmethods\'.committed": {"value": 26476544}, "vm.memory.pools.CodeHeap-\'non-profiled-nmethods\'.init": {"value": 2555904}, "vm.memory.pools.CodeHeap-\'non-profiled-nmethods\'.max": {"value": 122908672}, "vm.memory.pools.CodeHeap-\'non-profiled-nmethods\'.usage": {"value": 0.21102367780851133}, "vm.memory.pools.CodeHeap-\'non-profiled-nmethods\'.used": {"value": 25936640}, "vm.memory.pools.CodeHeap-\'profiled-nmethods\'.committed": {"value": 35979264}, "vm.memory.pools.CodeHeap-\'profiled-nmethods\'.init": {"value": 2555904}, "vm.memory.pools.CodeHeap-\'profiled-nmethods\'.max": {"value": 122908672}, "vm.memory.pools.CodeHeap-\'profiled-nmethods\'.usage": {"value": 0.2553008464691572}, "vm.memory.pools.CodeHeap-\'profiled-nmethods\'.used": {"value": 31378688}, "vm.memory.pools.Compressed-Class-Space.committed": {"value": 13631488}, "vm.memory.pools.Compressed-Class-Space.init": {"value": 0}, "vm.memory.pools.Compressed-Class-Space.max": {"value": 1073741824}, "vm.memory.pools.Compressed-Class-Space.usage": {"value": 0.011265315115451813}, "vm.memory.pools.Compressed-Class-Space.used": {"value": 12096040}, "vm.memory.pools.G1-Eden-Space.committed": {"value": 260046848}, "vm.memory.pools.G1-Eden-Space.init": {"value": 29360128}, "vm.memory.pools.G1-Eden-Space.max": {"value": -1}, "vm.memory.pools.G1-Eden-Space.usage": {"value": 0.4838709677419355}, "vm.memory.pools.G1-Eden-Space.used": {"value": 125829120}, "vm.memory.pools.G1-Eden-Space.used-after-gc": {"value": 0}, "vm.memory.pools.G1-Old-Gen.committed": {"value": 146800640}, "vm.memory.pools.G1-Old-Gen.init": {"value": 494927872}, "vm.memory.pools.G1-Old-Gen.max": {"value": 8342470656}, "vm.memory.pools.G1-Old-Gen.usage": {"value": 0.012662600847630719}, "vm.memory.pools.G1-Old-Gen.used": {"value": 105637376}, "vm.memory.pools.G1-Old-Gen.used-after-gc": {"value": 105637376}, "vm.memory.pools.G1-Survivor-Space.committed": {"value": 12582912}, "vm.memory.pools.G1-Survivor-Space.init": {"value": 0}, "vm.memory.pools.G1-Survivor-Space.max": {"value": -1}, "vm.memory.pools.G1-Survivor-Space.usage": {"value": 0.8234634399414062}, "vm.memory.pools.G1-Survivor-Space.used": {"value": 10361568}, "vm.memory.pools.G1-Survivor-Space.used-after-gc": {"value": 10361568}, "vm.memory.pools.Metaspace.committed": {"value": 113377280}, "vm.memory.pools.Metaspace.init": {"value": 0}, "vm.memory.pools.Metaspace.max": {"value": -1}, "vm.memory.pools.Metaspace.usage": {"value": 0.9357172795113801}, "vm.memory.pools.Metaspace.used": {"value": 106089080}, "vm.memory.total.committed": {"value": 611647488}, "vm.memory.total.init": {"value": 531955712}, "vm.memory.total.max": {"value": -1}, "vm.memory.total.used": {"value": 419967872}, "vm.new.count": {"value": 0}, "vm.peak.count": {"value": 63}, "vm.runnable.count": {"value": 11}, "vm.terminated.count": {"value": 0}, "vm.timed_waiting.count": {"value": 15}, "vm.total_started.count": {"value": 4306}, "vm.uptime.milliseconds": {"value": 60703154}, "vm.waiting.count": {"value": 12}}, "counters": {"http.activeRequests": {"count": 1}}, "meters": {"http.responseCodes.badRequest": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "http.responseCodes.created": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "http.responseCodes.forbidden": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "http.responseCodes.noContent": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "http.responseCodes.notFound": {"count": 3, "m15_rate": 0.05177609654545232, "m1_rate": 0.022564501638192222, "m5_rate": 0.0936903885612386, "mean_rate": 0.0029681732735664388, "units": "events/minute"}, "http.responseCodes.notModified": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "http.responseCodes.ok": {"count": 7128, "m15_rate": 5.0913522499837045, "m1_rate": 32.826238076162866, "m5_rate": 11.993338724906588, "mean_rate": 7.052379698649981, "units": "events/minute"}, "http.responseCodes.other": {"count": 5, "m15_rate": 2.8201116524330977e-30, "m1_rate": 1.77863632503e-312, "m5_rate": 6.077861230288915e-88, "mean_rate": 0.004946955456535154, "units": "events/minute"}, "http.responseCodes.serverError": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "http.responseCodes.serviceUnavailable": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "jenkins.job.scheduled": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "jenkins.runs.aborted": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "jenkins.runs.failure": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "jenkins.runs.not_built": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "jenkins.runs.success": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "jenkins.runs.total": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "jenkins.runs.unstable": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}, "jenkins.task.scheduled": {"count": 0, "m15_rate": 0.0, "m1_rate": 0.0, "m5_rate": 0.0, "mean_rate": 0.0, "units": "events/minute"}}}
                """
            ]
        ]
    )


def test_parsing_section_data(section: agent_module.Section) -> None:
    assert "gauges" in section
    assert "counters" in section


def test_discovery(section: agent_module.Section) -> None:
    assert list(agent_module.discover_jenkins_metrics_service(section)) == [
        Service(item="HTTP Requests"),
        Service(item="Memory"),
        Service(item="Threads"),
    ]


def test_jenkins_system_metrics_http_requests(section: agent_module.Section) -> None:
    expected_results = [
        Result(state=State.OK, summary="HTTP requests: active: 1"),
        Metric("jenkins_metrics_counter_http_activerequests", 1.0),
    ]
    assert (
        list(agent_module.check_jenkins_metrics("HTTP Requests", {}, section)) == expected_results
    )


def test_jenkins_system_metrics_memory(section: agent_module.Section) -> None:
    expected_results = [
        Result(state=State.OK, notice="JVM memory: heap: available by OS: 400 MiB"),
        Metric("jenkins_memory_vm_memory_heap_committed", 419430400.0),
        Result(state=State.OK, notice="JVM memory: heap: initially requested: 500 MiB"),
        Metric("jenkins_memory_vm_memory_heap_init", 524288000.0),
        Result(state=State.OK, notice="JVM memory: heap: max. allowed: 7.77 GiB"),
        Metric("jenkins_memory_vm_memory_heap_max", 8342470656.0),
        Result(state=State.OK, notice="JVM memory: heap: usage: 2.90%"),
        Metric("jenkins_memory_vm_memory_heap_usage", 2.898758341164491),
        Result(state=State.OK, summary="JVM memory: heap: used: 231 MiB"),
        Metric("jenkins_memory_vm_memory_heap_used", 241828064.0),
        Result(state=State.OK, notice="JVM memory: non-heap: available by OS: 183 MiB"),
        Metric("jenkins_memory_vm_memory_non_heap_committed", 192217088.0),
        Result(state=State.OK, notice="JVM memory: non-heap: initially requested: 7.31 MiB"),
        Metric("jenkins_memory_vm_memory_non_heap_init", 7667712.0),
        Result(state=State.OK, notice="JVM memory: non-heap: usage: 92.68%"),
        Metric("jenkins_memory_vm_memory_non_heap_usage", 92.67636392452268),
        Result(state=State.OK, summary="JVM memory: non-heap: used: 170 MiB"),
        Metric("jenkins_memory_vm_memory_non_heap_used", 178139808.0),
        Result(state=State.OK, notice="JVM memory pool G1-Eden-Space: available by OS: 248 MiB"),
        Metric("jenkins_memory_vm_memory_pools_g1_eden_space_committed", 260046848.0),
        Result(
            state=State.OK, notice="JVM memory pool G1-Eden-Space: initially requested: 28.0 MiB"
        ),
        Metric("jenkins_memory_vm_memory_pools_g1_eden_space_init", 29360128.0),
        Result(state=State.OK, notice="JVM memory pool G1-Eden-Space: usage: 48.39%"),
        Metric("jenkins_memory_vm_memory_pools_g1_eden_space_usage", 48.38709677419355),
        Result(state=State.OK, summary="JVM memory pool G1-Eden-Space: used: 120 MiB"),
        Metric("jenkins_memory_vm_memory_pools_g1_eden_space_used", 125829120.0),
        Result(state=State.OK, notice="JVM memory pool G1-Eden-Space: used after GC: 0 B"),
        Metric("jenkins_memory_vm_memory_pools_g1_eden_space_used_after_gc", 0.0),
        Result(state=State.OK, notice="JVM memory pool G1-Old-Gen: available by OS: 140 MiB"),
        Metric("jenkins_memory_vm_memory_pools_g1_old_gen_committed", 146800640.0),
        Result(state=State.OK, notice="JVM memory pool G1-Old-Gen: initially requested: 472 MiB"),
        Metric("jenkins_memory_vm_memory_pools_g1_old_gen_init", 494927872.0),
        Result(state=State.OK, notice="JVM memory pool G1-Old-Gen: max. allowed: 7.77 GiB"),
        Metric("jenkins_memory_vm_memory_pools_g1_old_gen_max", 8342470656.0),
        Result(state=State.OK, notice="JVM memory pool G1-Old-Gen: usage: 1.27%"),
        Metric("jenkins_memory_vm_memory_pools_g1_old_gen_usage", 1.2662600847630718),
        Result(state=State.OK, summary="JVM memory pool G1-Old-Gen: used: 101 MiB"),
        Metric("jenkins_memory_vm_memory_pools_g1_old_gen_used", 105637376.0),
        Result(state=State.OK, notice="JVM memory pool G1-Old-Gen: used after GC: 101 MiB"),
        Metric("jenkins_memory_vm_memory_pools_g1_old_gen_used_after_gc", 105637376.0),
        Result(
            state=State.OK, notice="JVM memory pool G1-Survivor-Space: available by OS: 12.0 MiB"
        ),
        Metric("jenkins_memory_vm_memory_pools_g1_survivor_space_committed", 12582912.0),
        Result(
            state=State.OK, notice="JVM memory pool G1-Survivor-Space: initially requested: 0 B"
        ),
        Metric("jenkins_memory_vm_memory_pools_g1_survivor_space_init", 0.0),
        Result(state=State.OK, notice="JVM memory pool G1-Survivor-Space: usage: 82.35%"),
        Metric("jenkins_memory_vm_memory_pools_g1_survivor_space_usage", 82.34634399414062),
        Result(state=State.OK, summary="JVM memory pool G1-Survivor-Space: used: 9.88 MiB"),
        Metric("jenkins_memory_vm_memory_pools_g1_survivor_space_used", 10361568.0),
        Result(state=State.OK, notice="JVM memory pool G1-Survivor-Space: used after GC: 9.88 MiB"),
        Metric("jenkins_memory_vm_memory_pools_g1_survivor_space_used_after_gc", 10361568.0),
        Result(state=State.OK, notice="JVM memory pool Metaspace: available by OS: 108 MiB"),
        Metric("jenkins_memory_vm_memory_pools_metaspace_committed", 113377280.0),
        Result(state=State.OK, notice="JVM memory pool Metaspace: initially requested: 0 B"),
        Metric("jenkins_memory_vm_memory_pools_metaspace_init", 0.0),
        Result(state=State.OK, notice="JVM memory pool Metaspace: usage: 93.57%"),
        Metric("jenkins_memory_vm_memory_pools_metaspace_usage", 93.571727951138),
        Result(state=State.OK, summary="JVM memory pool Metaspace: used: 101 MiB"),
        Metric("jenkins_memory_vm_memory_pools_metaspace_used", 106089080.0),
        Result(state=State.OK, notice="JVM memory: available by OS: 583 MiB"),
        Metric("jenkins_memory_vm_memory_total_committed", 611647488.0),
        Result(state=State.OK, notice="JVM memory: initially requested: 507 MiB"),
        Metric("jenkins_memory_vm_memory_total_init", 531955712.0),
        Result(state=State.OK, summary="JVM memory: used: 401 MiB"),
        Metric("jenkins_memory_vm_memory_total_used", 419967872.0),
    ]
    assert list(agent_module.check_jenkins_metrics("Memory", {}, section)) == expected_results


def test_jenkins_system_metrics_threads(section: agent_module.Section) -> None:
    expected_results = [
        Result(state=State.OK, summary="Total threads: 38"),
        Metric("jenkins_threads_vm_count", 38.0),
        Result(state=State.OK, summary="Blocked threads: 0"),
        Metric("jenkins_threads_vm_blocked_count", 0.0),
        Result(state=State.OK, summary="Active threads: 11"),
        Metric("jenkins_threads_vm_runnable_count", 11.0),
        Result(state=State.OK, summary="Unstarted threads: 0"),
        Metric("jenkins_threads_vm_new_count", 0.0),
        Result(state=State.OK, summary="Deadlocked threads: 0"),
        Metric("jenkins_threads_vm_deadlock_count", 0.0),
        Result(state=State.OK, summary="Daemon threads: 19"),
        Metric("jenkins_threads_vm_daemon_count", 19.0),
        Result(state=State.OK, summary="Waiting threads: 12"),
        Metric("jenkins_threads_vm_waiting_count", 12.0),
        Result(state=State.OK, summary="Timed waiting threads: 15"),
        Metric("jenkins_threads_vm_timed_waiting_count", 15.0),
        Result(state=State.OK, summary="Terminated threads: 0"),
        Metric("jenkins_threads_vm_terminated_count", 0.0),
    ]
    assert list(agent_module.check_jenkins_metrics("Threads", {}, section)) == expected_results
