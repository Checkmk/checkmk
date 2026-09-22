/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { type Ref, computed } from 'vue'

import type { PresentationElement } from '@/maps/types/api'

import { type ElementById, isConnectorShape, selectionBounds } from '../connectors'

interface SelectionGeometryOptions {
  selectedElements: Ref<PresentationElement[]>
  scale: Ref<number>
  byId: ElementById
}

/** The eight resize handles, named for the edge or corner they sit on. */
export type ResizeHandle = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w'

type HandleStyle = Record<string, string>

/** On-screen sizes, divided by the zoom so they stay constant while zooming. */
const HANDLE_PX = 10
const ROTATE_PX = 12
const ROTATE_OFFSET_PX = 26
const OUTLINE_PX = 1.5

/**
 * Read-only overlay geometry for the editor's current selection: the box it
 * spans (a connector contributes its endpoint extent, not its vestigial
 * x/y/w/h) and the resize/rotate handle styles. Pure derivation — no mutation,
 * no side effects.
 */
export function useSelectionGeometry(options: SelectionGeometryOptions) {
  const { selectedElements, scale, byId } = options

  const selectionBox = computed(() => selectionBounds(selectedElements.value, byId))

  const single = computed(() =>
    selectedElements.value.length === 1 ? selectedElements.value[0] : undefined
  )
  // A single selected connector has no resize/rotate handles (its geometry comes
  // from its endpoints), so the overlay shows only the selection outline.
  const singleIsConnector = computed(() => !!single.value && isConnectorShape(single.value))

  const selBoxStyle = computed(() => {
    const b = selectionBox.value
    if (!b) {
      return {}
    }
    // On a single rotated element the overlay rotates with it, so the handles
    // still sit on the element's own corners.
    const rotation = single.value?.rotation ?? 0
    return {
      left: `${b.x}px`,
      top: `${b.y}px`,
      width: `${b.w}px`,
      height: `${b.h}px`,
      outlineWidth: `${OUTLINE_PX / scale.value}px`,
      transform: rotation ? `rotate(${rotation}deg)` : 'none',
      transformOrigin: 'center center'
    }
  })

  // One computed for all eight: they differ only in where they sit, and they
  // all rescale together, so a per-handle call would recompute the same sizes
  // eight times per render of the selection overlay.
  const handleStyles = computed<Record<ResizeHandle, HandleStyle>>(() => {
    const size = HANDLE_PX / scale.value
    const at = (left: string, top: string): HandleStyle => ({
      width: `${size}px`,
      height: `${size}px`,
      left,
      top,
      marginLeft: `${-size / 2}px`,
      marginTop: `${-size / 2}px`,
      borderWidth: `${1 / scale.value}px`
    })
    return {
      nw: at('0%', '0%'),
      n: at('50%', '0%'),
      ne: at('100%', '0%'),
      e: at('100%', '50%'),
      se: at('100%', '100%'),
      s: at('50%', '100%'),
      sw: at('0%', '100%'),
      w: at('0%', '50%')
    }
  })

  const rotateHandleStyle = computed(() => {
    const size = ROTATE_PX / scale.value
    return {
      width: `${size}px`,
      height: `${size}px`,
      left: '50%',
      top: `${-ROTATE_OFFSET_PX / scale.value}px`,
      marginLeft: `${-size / 2}px`,
      borderWidth: `${1 / scale.value}px`
    }
  })

  return { selectionBox, singleIsConnector, selBoxStyle, handleStyles, rotateHandleStyle }
}
