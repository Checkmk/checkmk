/**
 * Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { Ref } from 'vue'

export enum AiRole {
  user = 'user',
  ai = 'ai',
  system = 'system'
}

export function typewriter(ref: Ref<string>, text: string, onTyped: () => void) {
  ref.value = ''
  const tokenSize = 20
  let i = 0
  const interval = setInterval(() => {
    if (i < text.length) {
      ref.value += text.substring(i, i + tokenSize)
      i += tokenSize
    } else {
      clearInterval(interval)
      onTyped()
    }
  }, 20)
}
