/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed, ref, watch } from 'vue'

import type { PresentationTemplate } from '../templates'

interface GalleryOptions {
  interactive: Ref<boolean>
  elementCount: () => number
  mapName: () => string
  /** Swaps theme and elements in one history step, so one undo restores them. */
  applyToSlide: (template: PresentationTemplate) => void
}

/**
 * The template gallery greets an empty slide once per map and session, and
 * stays reopenable from the slide settings. Applying a template over existing
 * elements replaces them, so that case asks first.
 */
export function useTemplateGallery(options: GalleryOptions) {
  const { interactive, elementCount, mapName, applyToSlide } = options

  const open = ref(false)
  const pending = ref<PresentationTemplate | null>(null)
  const seenKey = computed(() => `maps-pres-templates-seen:${mapName()}`)

  watch(
    [interactive, elementCount, mapName],
    ([editing, count]) => {
      if (editing && count === 0 && !sessionStorage.getItem(seenKey.value)) {
        open.value = true
      }
    },
    { immediate: true }
  )

  function dismiss(): void {
    sessionStorage.setItem(seenKey.value, '1')
    open.value = false
  }

  function run(template: PresentationTemplate): void {
    applyToSlide(template)
    dismiss()
  }

  function apply(template: PresentationTemplate): void {
    if (template.id === 'blank') {
      dismiss()
    } else if (elementCount()) {
      pending.value = template
    } else {
      run(template)
    }
  }

  function confirmPending(): void {
    const template = pending.value
    pending.value = null
    if (template) {
      run(template)
    }
  }

  return { open, pending, apply, confirmPending, dismiss }
}
