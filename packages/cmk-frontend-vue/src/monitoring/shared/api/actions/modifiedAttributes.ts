/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { components } from 'cmk-shared-typing/typescript/openapi_internal'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { HostRef } from '@/monitoring/shared/api/types'

/** What a command may switch off for a host or service until it is reset. */
export type ModifiableAttribute = components['schemas']['ToggleAttributeRequestBody']['attribute']

const JSON_HEADER = { header: { 'Content-Type': 'application/json' } } as const

export class ModifiedAttributesApi {
  public async toggleHosts(
    hosts: HostRef[],
    attribute: ModifiableAttribute,
    enabled: boolean
  ): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/toggle_attribute', {
        params: JSON_HEADER,
        body: { hosts, attribute, enabled }
      })
    )
    return response.modified
  }

  public async resetHosts(hosts: HostRef[]): Promise<number> {
    const response = unwrap(
      await client.POST('/monitor/hosts/actions/reset_modified_attributes', {
        params: JSON_HEADER,
        body: { hosts }
      })
    )
    return response.modified
  }
}
