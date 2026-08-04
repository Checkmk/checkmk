/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { HostRef } from '@/monitoring/shared/api/types'

import type { MonitoringAction } from './types'

export type MonitoringActionRegistry<Target = HostRef> = Record<
  string,
  MonitoringAction<unknown, Target>
>

export function createActionRegistry<Target = HostRef>(
  actions: MonitoringAction<unknown, Target>[]
): MonitoringActionRegistry<Target> {
  return Object.fromEntries(actions.map((action) => [action.id, action]))
}
