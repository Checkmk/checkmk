/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fromDate } from '@internationalized/date'

import type { ContentProps } from '@/dashboard/components/DashboardContent/types'

const TEST_RANGE = {
  from: fromDate(new Date('2026-01-01T00:00:00Z'), 'UTC'),
  to: fromDate(new Date('2026-01-01T01:00:00Z'), 'UTC')
}

export function makeContentProps<T>(
  content: T,
  overrides: Partial<Omit<ContentProps<T>, 'content'>> = {}
): ContentProps<T> {
  return {
    widget_id: 'test-widget',
    general_settings: {
      title: { text: 'Test', render_mode: 'with_background' },
      render_background: true
    },
    content,
    effectiveTitle: 'Test',
    effective_filter_context: { uses_infos: [], filters: {}, restricted_to_single: [] },
    dashboardKey: { owner: 'cmkadmin', name: 'main' },
    tick: 0,
    range: TEST_RANGE,
    ...overrides
  }
}
