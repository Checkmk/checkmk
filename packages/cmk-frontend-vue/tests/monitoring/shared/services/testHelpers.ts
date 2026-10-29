/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { KeyShortcutService } from 'cmk-ui-library/lib/keyShortcuts'
import { onTestFinished, vi } from 'vitest'

import {
  MonitoringService,
  type PagedResponse
} from '@/monitoring/shared/services/MonitoringService'

export function makeResponse<T>(
  items: T[],
  matched: number,
  total: number,
  limit = 1000
): PagedResponse<T> {
  return { items, meta: { limit, matched, total } }
}

export function makeKeyShortcutService(): KeyShortcutService {
  return {
    on: vi.fn(() => 'shortcut-id'),
    remove: vi.fn()
  } as unknown as KeyShortcutService
}

class EmptyListingService extends MonitoringService<unknown> {
  protected async fetchBatch(): Promise<PagedResponse<unknown>> {
    return makeResponse([], 0, 0)
  }
}

/** A listing with no rows, for a component under test to narrow; it stops polling on its own. */
export function makeListingService(): MonitoringService<unknown> {
  const service = new EmptyListingService('test-listing', makeKeyShortcutService())
  onTestFinished(() => service.destruct())
  return service
}
