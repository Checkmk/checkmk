/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type InjectionKey, inject, provide, ref, watch } from 'vue'

interface FlyoutNestingContext {
  /** Called by a child flyout when it opens. */
  registerOpen: () => void
  /** Called by a child flyout when it closes. */
  unregisterOpen: () => void
  /** Whether any direct child flyout is currently open. */
  hasOpenChild: () => boolean
}

const flyoutNestingKey: InjectionKey<FlyoutNestingContext> = Symbol('cmk-flyout-nesting')

/**
 * Wires a flyout into the nesting coordination: provides a context for child flyouts, registers
 * this flyout's open state with an enclosing flyout (if any), and reports whether a direct child
 * flyout is currently open.
 */
export function useFlyoutNesting(open: () => boolean): { hasOpenChild: () => boolean } {
  const openChildren = ref(0)
  const parentNesting = inject(flyoutNestingKey, null)

  const nestingContext: FlyoutNestingContext = {
    registerOpen: () => {
      openChildren.value += 1
    },
    unregisterOpen: () => {
      openChildren.value = Math.max(0, openChildren.value - 1)
    },
    hasOpenChild: () => openChildren.value > 0
  }
  provide(flyoutNestingKey, nestingContext)

  watch(open, (isOpen) => {
    if (isOpen) {
      parentNesting?.registerOpen()
    } else {
      parentNesting?.unregisterOpen()
    }
  })

  return { hasOpenChild: nestingContext.hasOpenChild }
}
