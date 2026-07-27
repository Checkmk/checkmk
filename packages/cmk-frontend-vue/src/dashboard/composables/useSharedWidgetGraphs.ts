/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject, provide } from 'vue'

import type { SharedWidgetGraphs } from '@/dashboard/types/page.ts'

const sharedWidgetGraphsKey: InjectionKey<Record<string, SharedWidgetGraphs>> =
  Symbol('sharedWidgetGraphs')

/**
 * The graph shells the backend discovered for a shared dashboard, by widget ID.
 *
 * A shared dashboard ships without filter values, so its graph widgets cannot discover their
 * own shells; they read them from here instead. Absent on an interactive dashboard, where the
 * widgets discover for themselves.
 */
export function useProvideSharedWidgetGraphs(value: Record<string, SharedWidgetGraphs>): void {
  provide(sharedWidgetGraphsKey, value)
}

export function useInjectSharedWidgetGraphs(): Record<string, SharedWidgetGraphs> | undefined {
  return inject(sharedWidgetGraphsKey, undefined)
}
