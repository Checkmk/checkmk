/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type ComputedRef, type MaybeRefOrGetter, computed, toValue } from 'vue'

export interface TeleportPlacement {
  target: ComputedRef<string>
  isDefault: ComputedRef<boolean>
}

export function useTeleportPlacement(
  defaultTarget: string,
  target: MaybeRefOrGetter<string | null | undefined>
): TeleportPlacement {
  const resolved = computed(() => toValue(target) ?? defaultTarget)
  return {
    target: resolved,
    isDefault: computed(() => resolved.value === defaultTarget)
  }
}
