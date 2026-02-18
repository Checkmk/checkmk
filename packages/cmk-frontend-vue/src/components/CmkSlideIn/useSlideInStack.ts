/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref } from 'vue'

type StackEntry = {
  id: string
  priority: number
  order: number
}

const openStack = ref<StackEntry[]>([])
let slideInIdCounter = 0
let slideInOrderCounter = 0

function removeFromStack(instanceId: string): void {
  const index = openStack.value.findIndex((entry) => entry.id === instanceId)
  if (index >= 0) {
    openStack.value.splice(index, 1)
  }
}

function sortStack(): void {
  openStack.value.sort((a, b) => {
    if (a.priority !== b.priority) {
      return a.priority - b.priority
    }
    return a.order - b.order
  })
}

export function useSlideInStack(stackPriority?: number | null): {
  instanceId: string
  isTopMost: Ref<boolean>
  register: () => void
  unregister: () => void
} {
  const instanceId = `cmk-slide-in-${++slideInIdCounter}`
  const priority = stackPriority ?? 0
  const isTopMost = computed(() => openStack.value[openStack.value.length - 1]?.id === instanceId)

  function register(): void {
    removeFromStack(instanceId)
    openStack.value.push({ id: instanceId, priority, order: ++slideInOrderCounter })
    sortStack()
  }

  function unregister(): void {
    removeFromStack(instanceId)
  }

  return { instanceId, isTopMost, register, unregister }
}
