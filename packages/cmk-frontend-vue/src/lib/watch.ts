/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { watch, onBeforeMount } from 'vue'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function isAsyncFunction<T, A extends any[]>(
  func: (...args: A) => T | Promise<T>
): func is (...args: A) => Promise<T> {
  return func.constructor.name === 'AsyncFunction'
}

export function immediateWatch<T>(
  getter: () => T,
  callback: ((value: T) => void) | ((value: T) => Promise<void>)
) {
  // This fixes a bug only visible in the browser.
  // Use this instead of the immediate flag on the watcher.
  // The immediate flag, when changing a ref that another computed() depends on will
  // result in a change which doesn't trigger a rerendering of the computed variable.
  if (isAsyncFunction<void, [T]>(callback)) {
    onBeforeMount(async () => await callback(getter()))
  } else {
    onBeforeMount(() => callback(getter()))
  }
  watch(getter, callback)
}
