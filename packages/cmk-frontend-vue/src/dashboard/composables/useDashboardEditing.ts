/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, type Ref, inject, provide, ref } from 'vue'

const dashboardEditingKey: InjectionKey<Readonly<Ref<boolean>>> = Symbol('dashboardEditing')

/** Whether the dashboard is being edited, so its widgets only show where they would link. */
export function useProvideDashboardEditing(editing: Readonly<Ref<boolean>>): void {
  provide(dashboardEditingKey, editing)
}

/** Holds false where nothing provides it, such as on a shared dashboard. */
export function useInjectDashboardEditing(): Readonly<Ref<boolean>> {
  return inject(dashboardEditingKey, ref(false))
}
