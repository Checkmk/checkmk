/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  type ComputedRef,
  type InjectionKey,
  type Ref,
  computed,
  inject,
  onBeforeUnmount,
  onMounted,
  provide,
  ref
} from 'vue'

import { MAX_PULSES } from '@/maps/utils/problemState'

const PULSE_COUNT: InjectionKey<Ref<number>> = Symbol('mapPulseCount')

/**
 * For a map canvas: whether more of its objects pulse than ``MAX_PULSES``, in
 * which case none of them should. Counting the pulses themselves rather than
 * states leaves out whatever the canvas does not draw as pulsing.
 */
export function providePulseCount(): ComputedRef<boolean> {
  const count = ref(0)
  provide(PULSE_COUNT, count)
  return computed(() => count.value > MAX_PULSES)
}

/** For a pulse: counts it on the canvas it sits on, for as long as it is drawn. */
export function countPulse(): void {
  const count = inject(PULSE_COUNT, null)
  if (count === null) {
    return
  }
  onMounted(() => count.value++)
  onBeforeUnmount(() => count.value--)
}
