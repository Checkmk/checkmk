/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type InjectionKey, computed, inject, provide } from 'vue'

const floatingTargetKey: InjectionKey<() => HTMLElement | undefined> = Symbol('cmk-floating-target')

/**
 * Register a container (slide-in, popup, flyout, …) as the floating target for its descendants by
 * providing a getter for its element. A nested container shadows an outer one, so descendants
 * always resolve their nearest layer.
 */
export function provideFloatingTarget(getTarget: () => HTMLElement | undefined): void {
  provide(floatingTargetKey, getTarget)
}

/** Nearest floating target for teleporting floating content. */
export function useFloatingTarget(): ComputedRef<HTMLElement | undefined> {
  const getTarget = inject(floatingTargetKey, () => undefined)
  return computed(() => getTarget())
}

const floatingBoundaryKey: InjectionKey<() => Element | undefined> = Symbol('cmk-floating-boundary')

/** Keep floating popups of descendants within this element, e.g. where a sticky header covers them. */
export function provideFloatingBoundary(getBoundary: () => Element | undefined): void {
  provide(floatingBoundaryKey, getBoundary)
}

/** Nearest floating boundary, if any. */
export function useFloatingBoundary(): ComputedRef<Element | undefined> {
  const getBoundary = inject(floatingBoundaryKey, () => undefined)
  return computed(() => getBoundary())
}
