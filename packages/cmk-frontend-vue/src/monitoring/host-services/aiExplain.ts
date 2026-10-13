/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ExplainThisIssueData } from 'cmk-shared-typing/typescript/ai_button'

import type { HostEntry, HostServiceEntry } from '@/monitoring/shared/api/types'

export const AI_EXPLAIN_ACTION_ID = 'explain_with_ai'

export interface ExplainedService {
  hostName: string
  hostState: HostEntry['state']
  serviceName: string
  serviceState: HostServiceEntry['state']
  stale: boolean
}

const SERVICE_STATES: Record<HostServiceEntry['state'], ExplainThisIssueData['service_state']> = {
  OK: 'OK',
  WARN: 'Warning',
  CRIT: 'Critical',
  UNKNOWN: 'Unknown',
  PENDING: 'Pending'
}

const HOST_STATES: Record<HostEntry['state'], ExplainThisIssueData['host_state']> = {
  UP: 'Up',
  DOWN: 'Down',
  UNREACHABLE: 'Unreachable',
  // The AI explain schema has no pending host state; a never-checked host is treated as up,
  // matching classic's ``explain_with_ai_icon.py`` fallback for an unrecognized host state.
  PENDING: 'Up'
}

export function requestAiExplanation(service: ExplainedService): void {
  const detail: ExplainThisIssueData = {
    host_name: service.hostName,
    service_name: service.serviceName,
    service_state: SERVICE_STATES[service.serviceState],
    host_state: HOST_STATES[service.hostState],
    is_stale: service.stale
  }
  document.dispatchEvent(new CustomEvent('cmk-ai-explain-button', { detail }))
}
