/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, ref, watch } from 'vue'

export function useDebounceRef<T>(value: Ref<T>, delay = 300, immediate: boolean = false): Ref<T> {
  const debounced = ref(value.value) as Ref<T>
  let timeout: ReturnType<typeof setTimeout> | null = null

  watch(
    value,
    (newValue) => {
      if (timeout) {
        clearTimeout(timeout)
      }

      timeout = setTimeout(() => {
        debounced.value = newValue
      }, delay)
    },
    { immediate: immediate }
  )

  return debounced
}

export function useDebounceFn(fn: CallableFunction, delay = 300, immediate: boolean = false) {
  const timeout = ref<ReturnType<typeof setTimeout> | null>(null)

  if (immediate) {
    fn()
  }

  return function () {
    if (timeout.value) {
      clearTimeout(timeout.value)
    }

    timeout.value = setTimeout(() => {
      fn()
    }, delay)
  }
}
