/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { CmkApiError } from 'cmk-ui-library/lib/error'
import client, { unwrap } from 'cmk-ui-library/lib/rest-api-client/client'

import type { CustomServiceDefinition } from './definition'

export interface SaveResult {
  ok: boolean
  error?: string
}

export async function saveCustomServiceDefinition(
  definition: CustomServiceDefinition
): Promise<SaveResult> {
  try {
    unwrap(
      await client.POST('/domain-types/custom_service/collections/all', {
        params: { header: { 'Content-Type': 'application/json' } },
        body: definition
      })
    )
    return { ok: true }
  } catch (error) {
    if (error instanceof CmkApiError && error.statusCode < 500) {
      return { ok: false, error: error.message }
    }
    throw error
  }
}
