/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, type Ref, computed, inject, provide } from 'vue'

const missingRuntimeFiltersActionKey = Symbol() as InjectionKey<Ref<null | (() => void)>>

export function useProvideMissingRuntimeFiltersAction(
  areAllMandatoryFiltersApplied: Ref<boolean>,
  openDashboardFilterSettings: Ref<boolean>
) {
  provide(
    missingRuntimeFiltersActionKey,
    computed(() => {
      return areAllMandatoryFiltersApplied.value
        ? null
        : () => (openDashboardFilterSettings.value = true)
    })
  )
}

export function useInjectMissingRuntimeFiltersAction() {
  const missingRuntimeFiltersAction = inject(missingRuntimeFiltersActionKey)
  if (!missingRuntimeFiltersAction) {
    throw new Error('no provider for missingRuntimeFiltersAction')
  }
  return missingRuntimeFiltersAction
}
