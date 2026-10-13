/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref, watch } from 'vue'

import { useTheme } from './useTheme'

const { currentTheme } = useTheme()
const isLegacyCssEnabled = ref(true)

async function setCss(enabled: boolean, theme: string) {
  const stylesheet = document.getElementById('cmk-theming-stylesheet') as HTMLLinkElement | null
  if (!stylesheet) {
    return
  }
  stylesheet.href = enabled
    ? (await import(`~cmk-frontend/themes/${theme}/theme.css?url`)).default
    : ''
}

let initialized = false

export function useLegacyCss() {
  if (!initialized) {
    initialized = true
    watch(
      [isLegacyCssEnabled, currentTheme],
      async ([enabled, theme]) => {
        await setCss(enabled, theme)
      },
      { immediate: true }
    )
  }

  return { isLegacyCssEnabled }
}
