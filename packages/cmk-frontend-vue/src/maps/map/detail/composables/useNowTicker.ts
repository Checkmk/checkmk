/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * A clock the drawer's ageing labels hang off.
 *
 * "2m ago", "in 30s" and "overdue" have to move on their own: monitoring
 * pushes a state change once, and the operator then watches the age of it. One
 * ticker for the whole drawer, stopped with the component.
 */
import { type Ref, onUnmounted, ref } from 'vue'

export function useNowTicker(intervalMs = 1000): Ref<number> {
  const nowMs = ref(Date.now())
  const timer = setInterval(() => {
    nowMs.value = Date.now()
  }, intervalMs)
  onUnmounted(() => clearInterval(timer))
  return nowMs
}
