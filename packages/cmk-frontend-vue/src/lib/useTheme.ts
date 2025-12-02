/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { onMounted, onUnmounted, ref } from 'vue'

export function useTheme() {
  const theme = ref(document.body.getAttribute('data-theme') || 'facelift')

  let observer: MutationObserver | null = null

  onMounted(() => {
    observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
          theme.value = document.body.getAttribute('data-theme') || 'facelift'
        }
      })
    })

    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ['data-theme']
    })
  })

  onUnmounted(() => {
    if (observer) {
      observer.disconnect()
    }
  })

  return {
    theme
  }
}
