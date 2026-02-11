/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, type MaybeRefOrGetter, type Ref, inject, provide, toRef } from 'vue'

import type { DashboardConstants } from '@/dashboard/types/dashboard'

const dashboardConstantsKey: InjectionKey<Ref<DashboardConstants | undefined>> =
  Symbol('dashboardConstants')

export function useProvideDashboardConstants(
  constants: MaybeRefOrGetter<DashboardConstants | undefined>
) {
  provide(dashboardConstantsKey, toRef(constants))
}

export function useInjectDashboardConstants(): DashboardConstants {
  const constantsRef = inject(dashboardConstantsKey)
  if (!constantsRef) {
    throw new Error('no provider for dashboardConstants')
  }
  if (!constantsRef.value) {
    throw new Error('dashboardConstants not yet loaded')
  }
  return constantsRef.value
}
