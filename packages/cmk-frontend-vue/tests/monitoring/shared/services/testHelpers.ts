/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { vi } from 'vitest'

import type { KeyShortcutService } from '@/lib/keyShortcuts'

import type { PagedResponse } from '@/monitoring/shared/services/MonitoringService'

export function makeResponse<T>(items: T[], total: number): PagedResponse<T> {
  return { items, meta: { total } }
}

export function makeKeyShortcutService(): KeyShortcutService {
  return {
    on: vi.fn(() => 'shortcut-id'),
    remove: vi.fn()
  } as unknown as KeyShortcutService
}
