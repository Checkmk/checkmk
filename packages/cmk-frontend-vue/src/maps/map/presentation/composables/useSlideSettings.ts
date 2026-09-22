/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import usei18n from 'cmk-ui-library/lib/i18n'
import type { Ref } from 'vue'

import { useToast } from '@/maps/services/context'
import type { PresentationElement, PresentationView } from '@/maps/types/api'

import { type ElementById, elementBounds } from '../connectors'

interface SlideSettingsOptions {
  view: Ref<PresentationView>
  elements: Ref<PresentationElement[]>
  byId: ElementById
  scheduleSave: () => void
}

/** The slide size the schema accepts, in slide units. */
const MIN_SIDE = 320
const MAX_SIDE = 8192

function clampSide(next: number, current: number): number {
  return Math.min(MAX_SIDE, Math.max(MIN_SIDE, Math.round(next) || current))
}

/**
 * Slide-level changes -- theme, size, background -- are map metadata rather
 * than element edits, so they save without touching the element undo history.
 *
 * Elements keep their absolute positions across a size change (Figma-style),
 * which means a smaller slide can silently cut some of them off. That is worth
 * a warning, not a refusal: the operator may well be about to move them.
 */
export function useSlideSettings(options: SlideSettingsOptions) {
  const { _t } = usei18n()
  const toast = useToast()
  const { view, elements, byId, scheduleSave } = options

  function warnAboutClipping(): void {
    const clipped = elements.value.some((el) => {
      const b = elementBounds(el, byId)
      return b.x + b.w > view.value.width || b.y + b.h > view.value.height
    })
    if (clipped) {
      toast.warning(_t('Some elements now extend beyond the slide — move or resize them.'))
    }
  }

  function change(patch: Partial<PresentationView>): void {
    const next = { ...view.value, ...patch }
    next.width = clampSide(next.width, view.value.width)
    next.height = clampSide(next.height, view.value.height)
    const shrunk = next.width < view.value.width || next.height < view.value.height
    view.value = next
    if (shrunk) {
      warnAboutClipping()
    }
    scheduleSave()
  }

  return { change }
}
