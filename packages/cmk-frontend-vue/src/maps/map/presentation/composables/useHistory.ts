/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { computed, ref } from 'vue'

// Snapshot-based undo/redo. The owner holds the live state and asks this stack
// to record a snapshot *before* each committed change; undo/redo hand back the
// snapshot to apply. State is serialised so snapshots are immutable copies.
export function useHistory<T>(
  serialize: (v: T) => string,
  deserialize: (s: string) => T,
  limit = 100
) {
  const past = ref<string[]>([])
  const future = ref<string[]>([])
  // Bumped by every stack movement. An owner that coalesces repeats into one
  // step (a held arrow key, say) watches this to tell whether the step it is
  // still adding to is the one on top of the stack.
  const version = ref(0)

  const canUndo = computed(() => past.value.length > 0)
  const canRedo = computed(() => future.value.length > 0)

  function record(current: T): void {
    past.value.push(serialize(current))
    if (past.value.length > limit) {
      past.value.shift()
    }
    future.value = []
    version.value++
  }

  function undo(current: T): T | null {
    if (past.value.length === 0) {
      return null
    }
    future.value.push(serialize(current))
    version.value++
    return deserialize(past.value.pop() as string)
  }

  function redo(current: T): T | null {
    if (future.value.length === 0) {
      return null
    }
    past.value.push(serialize(current))
    version.value++
    return deserialize(future.value.pop() as string)
  }

  function reset(): void {
    past.value = []
    future.value = []
    version.value++
  }

  return { canUndo, canRedo, version, record, undo, redo, reset }
}
