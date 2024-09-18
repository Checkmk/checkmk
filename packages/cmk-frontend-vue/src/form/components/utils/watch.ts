/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { watch, onBeforeMount } from 'vue'

export function immediateWatch<T>(getter: () => T, callback: (value: T) => void) {
  // This fixes a bug only visible in the browser.
  // Use this instead of the immediate flag on the watcher.
  // The immediate flag, when changing a ref that another computed() depends on will
  // result in a change which doesn't trigger a rerendering of the computed variable.
  onBeforeMount(() => {
    callback(getter())
  })
  watch(getter, callback)
}
