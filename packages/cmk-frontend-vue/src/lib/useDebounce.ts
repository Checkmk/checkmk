/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, onUnmounted, ref, watch } from 'vue'

export function useDebounceRef<T>(value: Ref<T>, delay = 300, immediate: boolean = false): Ref<T> {
  const debounced = ref(value.value) as Ref<T>
  const timeout = ref<ReturnType<typeof setTimeout> | null>(null)

  onUnmounted(() => {
    if (timeout.value) {
      clearTimeout(timeout.value)
    }
  })

  watch(
    value,
    (newValue) => {
      if (timeout.value) {
        clearTimeout(timeout.value)
      }

      timeout.value = setTimeout(() => {
        debounced.value = newValue
      }, delay)
    },
    { immediate: immediate }
  )

  return debounced
}

type DebouncedFunction<T extends (...args: unknown[]) => void> = (...args: Parameters<T>) => void

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function useDebounceFn<T extends (...args: any[]) => void>(
  fn: T,
  delay: number = 300
): DebouncedFunction<T> {
  const timeout = ref<ReturnType<typeof setTimeout> | null>(null)

  const debouncedFn = (...args: Parameters<T>) => {
    if (timeout.value) {
      clearTimeout(timeout.value)
    }

    timeout.value = setTimeout(() => {
      fn(...args)
    }, delay)
  }

  onUnmounted(() => {
    if (timeout.value) {
      clearTimeout(timeout.value)
    }
  })

  return debouncedFn
}
