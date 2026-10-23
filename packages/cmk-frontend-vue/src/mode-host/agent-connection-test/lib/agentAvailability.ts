/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { paths } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

const AVAILABILITY_PATH = '/domain-types/agent/actions/availability/invoke'

export type AgentPackageType =
  paths[typeof AVAILABILITY_PATH]['get']['parameters']['query']['os_type']

/** Whether the Agent Bakery has a package of this type baked for the host. */
export async function isAgentBaked(hostName: string, osType: AgentPackageType): Promise<boolean> {
  const data = unwrap(
    await client.GET(AVAILABILITY_PATH, {
      params: { query: { host_name: hostName, os_type: osType } }
    })
  )
  return data.available
}
