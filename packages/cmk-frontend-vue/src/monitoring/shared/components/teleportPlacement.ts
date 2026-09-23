/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type ComputedRef,
  type InjectionKey,
  type MaybeRefOrGetter,
  computed,
  inject,
  provide,
  toValue
} from 'vue'

export interface TeleportPlacement {
  target: ComputedRef<string>
  isDefault: ComputedRef<boolean>
}

const IS_DEFAULT_PLACEMENT: InjectionKey<ComputedRef<boolean>> = Symbol('isDefaultPlacement')

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

export function provideTeleportPlacement(
  defaultTarget: string,
  target: MaybeRefOrGetter<string | null | undefined>
): TeleportPlacement {
  const placement = useTeleportPlacement(defaultTarget, target)
  provide(IS_DEFAULT_PLACEMENT, placement.isDefault)
  return placement
}

export function useIsDefaultPlacement(): ComputedRef<boolean> {
  return inject(
    IS_DEFAULT_PLACEMENT,
    computed(() => true)
  )
}
