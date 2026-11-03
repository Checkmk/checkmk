/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, type Ref, inject, provide, ref } from 'vue'

const drillDownSourceKey: InjectionKey<Readonly<Ref<string | null>>> = Symbol('drillDownSource')

/** The title of the dashboard its widgets' drill-downs leave, for the way back. */
export function useProvideDrillDownSource(title: Readonly<Ref<string>>): void {
  provide(drillDownSourceKey, title)
}

/** Holds null where nothing provides a title, such as on a shared dashboard. */
export function useInjectDrillDownSource(): Readonly<Ref<string | null>> {
  return inject(drillDownSourceKey, ref(null))
}
