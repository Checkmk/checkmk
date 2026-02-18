/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject, provide } from 'vue'

const isPublicDashboardKey: InjectionKey<boolean> = Symbol('isPublicDashboard')

export function useProvideIsPublicDashboard(): void {
  provide(isPublicDashboardKey, true)
}

export function useInjectIsPublicDashboard(): boolean {
  return inject(isPublicDashboardKey, false)
}

export function useSuppressEventOnPublicDashboard(): (event: MouseEvent | KeyboardEvent) => void {
  const isPublicDashboard = useInjectIsPublicDashboard()
  return (event: MouseEvent | KeyboardEvent): void => {
    if (isPublicDashboard) {
      event.preventDefault()
      event.stopImmediatePropagation()
    }
  }
}
