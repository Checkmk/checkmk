/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ExplainThisIssueData } from 'cmk-shared-typing/typescript/ai_button'

import type { StreamEvent } from '@/ai/lib/ai-api-client'

export type FixtureId =
  | 'cpu-fan-critical'
  | 'filesystem-warning'
  | 'medium-confidence'
  | 'low-confidence'
  | 'pending'

export interface Fixture {
  label: string
  events: StreamEvent[]
  context_data?: Partial<ExplainThisIssueData>
}

// Fixtures 1 and 2 mirror the two worked examples baked into the
// `explain_this_service` system prompt in
// cloudmk/ai_service/src/ai_service/prompts/explanation_prompts/
//   explain_this_service_prompt.py
//
// Fixture 3 mirrors the hardcoded pending-state response in
// cloudmk/ai_service/src/ai_service/service/panopticon_service.py
// (used when service_state is None).
export const fixtures: Record<FixtureId, Fixture> = {
  'cpu-fan-critical': {
    label: 'CPU fan failure (Critical)',
    events: [
      { type: 'metadata', model: 'mock-model' },
      { type: 'answer', text: '# Summary\n' },
      {
        type: 'answer',
        text:
          'The CPU fan is spinning well below its critical lower threshold, ' +
          'indicating it has failed or stalled. The CPU temperature service is ' +
          'also **WARN** and climbing, corroborating a causal link: loss of ' +
          'active cooling is driving thermal rise. At the current rate of ' +
          'increase, the thermal protection threshold may be reached within ' +
          '2 hours.\n\n'
      },
      {
        type: 'answer',
        text:
          '| Metric | Value | Status |\n' +
          '|--------|-------|--------|\n' +
          '| CPU fan RPM | 120 RPM | CRIT |\n' +
          '| Lower critical threshold | 800 RPM |  |\n' +
          '| CPU temperature | 78 °C | WARN |\n\n'
      },
      { type: 'answer', text: 'Confidence: **High**\n\n' },
      { type: 'answer', text: '# Service context\n' },
      {
        type: 'answer',
        text:
          '* **The service:** CPU fan speed monitoring tracks the RPM of the ' +
          'processor cooling fan to detect mechanical failure or power loss ' +
          'to the fan controller.\n' +
          '* **The failure:** A stalled CPU fan leads to thermal throttling, ' +
          'unexpected shutdowns, and permanent CPU damage if the host is not ' +
          'powered down.\n\n'
      },
      { type: 'answer', text: '# Recommended actions\n' },
      {
        type: 'answer',
        text:
          '1. **Verify fan scope**: Check the full hardware sensor inventory ' +
          'to determine whether the failure is isolated to one slot or ' +
          'affects all chassis fans.\n' +
          '2. **Power down host**: Shut down the host as a precaution if the ' +
          'temperature continues to rise while the fan failure is confirmed.\n' +
          '3. **Replace fan unit**: Swap the failed fan and confirm RPM ' +
          'returns to normal range before bringing the host back to full load.\n'
      },
      { type: 'finish' }
    ]
  },

  'filesystem-warning': {
    label: 'Filesystem usage (Warning)',
    context_data: {
      service_name: 'Filesystem usage',
      service_state: 'Warning'
    },
    events: [
      { type: 'metadata', model: 'mock-model' },
      { type: 'answer', text: '# Summary\n' },
      {
        type: 'answer',
        text:
          'The root filesystem is in **WARN** state, having crossed the ' +
          '80% usage threshold. All other services on the host are **OK**, ' +
          'suggesting this is an isolated storage growth issue rather than a ' +
          'broader infrastructure problem. Based on the current fill rate, ' +
          'full capacity will be reached in approximately 6 days.\n\n'
      },
      {
        type: 'answer',
        text:
          '| Metric | Value | Status |\n' +
          '|--------|-------|--------|\n' +
          '| Used | 82 % | WARN |\n' +
          '| Available | 18 GB |  |\n' +
          '| Inodes used | 45 % | OK |\n\n'
      },
      { type: 'answer', text: 'Confidence: **High**\n\n' },
      { type: 'answer', text: '# Service context\n' },
      {
        type: 'answer',
        text:
          '* **The service:** Filesystem usage monitoring tracks disk space ' +
          'consumption on a mount point, alerting before full capacity ' +
          'causes write failures.\n' +
          '* **The failure:** A full filesystem prevents log writes, ' +
          'database transactions, and application temporary file creation, ' +
          'often causing cascading service failures without clear error ' +
          'messages.\n\n'
      },
      { type: 'answer', text: '# Recommended actions\n' },
      {
        type: 'answer',
        text:
          '1. **Identify top consumers**: Locate the largest directories on ' +
          'the volume to determine whether growth is driven by logs, ' +
          'application data, or unexpected files.\n' +
          '2. **Rotate or archive logs**: Archive or rotate log files if log ' +
          'directories are the primary consumers.\n' +
          '3. **Expand the volume**: Grow the mount point before usage ' +
          'crosses the critical threshold if the growth rate cannot be ' +
          'controlled.\n'
      },
      { type: 'finish' }
    ]
  },

  'medium-confidence': {
    label: 'Memory pressure (Medium confidence)',
    context_data: {
      host_name: 'very-long-hostname-that-should-trigger-overflow-behavior.prod.example.com',
      service_name: 'Memory pressure monitoring with an unusually long service description name'
    },
    events: [
      { type: 'metadata', model: 'mock-model' },
      { type: 'answer', text: '# Summary\n' },
      {
        type: 'answer',
        text:
          'Memory usage has climbed above the warning threshold and is ' +
          'currently at 91%. The trend over the last 24 hours shows steady ' +
          'growth, but several non-monitored kernel caches may be inflating ' +
          'the reading. A leak in one of the application processes is the ' +
          'most likely cause, though kernel-managed buffers could also ' +
          'account for some of the growth.\n\n'
      },
      {
        type: 'answer',
        text:
          '| Metric | Value | Status |\n' +
          '|--------|-------|--------|\n' +
          '| Used memory | 91 % | WARN |\n' +
          '| Available | 720 MB |  |\n' +
          '| Swap usage | 12 % | OK |\n\n'
      },
      { type: 'answer', text: 'Confidence: **Medium**\n\n' },
      { type: 'answer', text: '# Service context\n' },
      {
        type: 'answer',
        text:
          '* **The service:** RAM utilization monitoring tracks the share ' +
          'of physical memory in use by user processes and the kernel, ' +
          'after accounting for reclaimable caches.\n' +
          '* **The failure:** When physical memory is exhausted, the kernel ' +
          'falls back to swap, which slows the entire system because swap ' +
          'I/O is orders of magnitude slower than RAM. If swap is also ' +
          'depleted, the kernel OOM killer terminates processes by their ' +
          '`oom_score`, typically targeting the largest unprivileged ' +
          'consumer first. This can take down database servers, application ' +
          'workers, or system services without warning, leading to ' +
          'cascading outages that are hard to diagnose because the killed ' +
          'process leaves no graceful shutdown trace.\n\n'
      },
      { type: 'answer', text: '# Recommended actions\n' },
      {
        type: 'answer',
        text:
          '1. **Identify the largest consumer**: Use `ps aux --sort=-rss | ' +
          'head` or `smem -tr` on the host to confirm which process is ' +
          'holding the most resident memory.\n' +
          '2. **Check for leaks**: Compare the RSS trend of the suspect ' +
          'process over the last 24 hours; a leak grows monotonically while ' +
          'a normal working set oscillates.\n' +
          '3. **Tune or restart**: Restart the leaking service as a ' +
          'temporary fix and open a ticket for the root cause.\n'
      },
      { type: 'finish' }
    ]
  },

  'low-confidence': {
    label: 'Intermittent latency spike (Low confidence)',
    events: [
      { type: 'metadata', model: 'mock-model' },
      { type: 'answer', text: '# Summary\n' },
      {
        type: 'answer',
        text:
          'A handful of network latency probes failed in the last 15 ' +
          'minutes, but the host itself reports healthy and other services ' +
          'are stable. The pattern does not match a typical link saturation ' +
          'or queue-drop scenario, and without packet captures it is hard ' +
          'to attribute the spikes to a single cause.\n\n'
      },
      {
        type: 'answer',
        text:
          '| Metric | Value | Status |\n' +
          '|--------|-------|--------|\n' +
          '| Avg RTT | 142 ms | WARN |\n' +
          '| Packet loss | 0.5 % | OK |\n' +
          '| Jitter | 38 ms | WARN |\n\n'
      },
      { type: 'answer', text: 'Confidence: **Low**\n\n' },
      { type: 'answer', text: '# Service context\n' },
      {
        type: 'answer',
        text:
          '* **The service:** Active probing measures round-trip time and ' +
          'jitter between the monitoring server and the target host.\n' +
          '* **The failure:** Elevated jitter without sustained packet loss ' +
          'often points to bufferbloat or contention on intermediate hops ' +
          'rather than a saturated last-mile link.\n\n'
      },
      { type: 'answer', text: '# Recommended actions\n' },
      {
        type: 'answer',
        text:
          '1. **Capture an MTR or traceroute during a spike**: Open an SSH ' +
          'session to the monitoring host and run ' +
          '`mtr --report --report-cycles=100 <target>` while a spike is in ' +
          'progress. The hop where the latency starts climbing identifies ' +
          'the path segment responsible. Save the output so the network ' +
          'team can correlate it with their own counters before considering ' +
          'a reroute, and attach the file to the incident ticket so the ' +
          'on-call has the evidence ready when the upstream provider is ' +
          'contacted.\n' +
          '2. **Compare with passive monitoring**: Cross-check the spike ' +
          'against flow-level telemetry from the routers along the path.\n' +
          '3. **Open an investigation ticket**: If MTR points at an ' +
          'external hop, file with the upstream provider.\n'
      },
      { type: 'finish' }
    ]
  },

  pending: {
    label: 'Pending (no monitoring data yet)',
    events: [
      { type: 'metadata', model: 'mock-model' },
      {
        type: 'thinking',
        text:
          '**Checking service state**\n\n' +
          'No check result has come in yet, so there is no monitoring data ' +
          "to work with. I'll explain what this state means and what the " +
          'user can do to move past it.'
      },
      { type: 'answer', text: '# Summary\n' },
      {
        type: 'answer',
        text:
          'This service is in **pending** state — Checkmk has not yet ' +
          'received a check result for it, so there is no monitoring data ' +
          'to analyze.\n\n'
      },
      { type: 'answer', text: '# Service context\n' },
      {
        type: 'answer',
        text:
          'A service enters pending state after it has been discovered and ' +
          'configured for the first time, but before its initial check was ' +
          'run.\n' +
          'To resolve this immediately, use the **Reschedule this check** ' +
          'command in the action menu of the affected service.\n' +
          'Otherwise, the service will transition to a real state (OK, ' +
          'Warning, or Critical) after its next scheduled check, typically ' +
          'within one minute.'
      },
      { type: 'finish' }
    ]
  }
}
