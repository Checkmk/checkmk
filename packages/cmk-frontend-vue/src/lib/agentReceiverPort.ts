/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

export const DEFAULT_AGENT_RECEIVER_PORT = 8000

export interface AgentReceiverPortResult {
  port: number
  isDefault: boolean
}

export async function fetchAgentReceiverPort(siteId: string): Promise<AgentReceiverPortResult> {
  try {
    const res = await fetch(
      `wato_ajax_agent_receiver_port.py?site_id=${encodeURIComponent(siteId)}`
    )
    if (res.ok) {
      const data = await res.json()
      if (data.result_code === 0 && data.result?.port !== undefined && data.result?.port !== null) {
        return { port: data.result.port, isDefault: data.result.is_default === true }
      }
    }
  } catch {
    // fall through to default
  }
  return { port: DEFAULT_AGENT_RECEIVER_PORT, isDefault: true }
}
