/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * The hover card and the right-click menu on a map's objects.
 *
 * Both are anchored to the pointer and both close on the same events, so they
 * are one piece of state rather than two: opening either closes the other, and
 * anything that takes the operator elsewhere closes both.
 *
 * The templates the card and the menu render come from three places — the
 * object, the map, the site — in that order, so a map can set a house style and
 * a single object can still override it.
 */
import { type ComputedRef, computed, reactive } from 'vue'

import {
  type HoverOpenOptions,
  useObjectHoverMenu
} from '@/maps/map/composables/useObjectHoverMenu'
import { useSettings } from '@/maps/services/context'
import type { MapConfig, MapElement, ObjectState } from '@/maps/types/api'
import { resolveTemplate } from '@/maps/utils/template'

export interface MapObjectMenus {
  hover: ReturnType<typeof useObjectHoverMenu>
  context: {
    visible: boolean
    object: MapElement | null
    x: number
    y: number
  }
  /** The right-clicked object's live state, where it has one. */
  contextState: ComputedRef<{ state?: ObjectState }>
  hoverTemplate: ComputedRef<string | null>
  contextTemplate: ComputedRef<string | null>
  openHover: (object: MapElement, event: MouseEvent | null, options?: HoverOpenOptions) => void
  /** A synthesised object — a BI subtree node — carries its own state. */
  openSubtreeHover: (object: MapElement, state: ObjectState, event: MouseEvent) => void
  openContext: (object: MapElement, event: MouseEvent) => void
  close: () => void
}

export function useMapObjectMenus(source: {
  /** ``null`` while the page has no map loaded. */
  config: () => MapConfig | null
  /**
   * The live state of an object, where the map has one for it. A map whose
   * objects are placed reads the states store; a map drawn from a live query
   * has to derive it, which is why this is the map type's to answer.
   */
  stateOf: (objectId: string) => ObjectState | undefined
  /** The settings preview is not interactive. */
  preview: () => boolean
}): MapObjectMenus {
  const settings = useSettings()
  const hover = useObjectHoverMenu({ resolveState: (object) => source.stateOf(object.id) })
  const context = reactive({
    visible: false,
    object: null as MapElement | null,
    x: 0,
    y: 0
  })

  function close(): void {
    hover.close()
    context.visible = false
  }

  return {
    hover,
    context,
    // An optional prop rejects an explicit undefined under
    // exactOptionalPropertyTypes, so the state is spread in only when present.
    contextState: computed(() => {
      const state = context.object ? source.stateOf(context.object.id) : undefined
      return state !== undefined ? { state } : {}
    }),
    hoverTemplate: computed(() =>
      resolveTemplate(
        hover.hover.object?.hover_template,
        source.config()?.hover_template,
        settings.settings.value.hover_template
      )
    ),
    contextTemplate: computed(() =>
      resolveTemplate(
        context.object?.context_template,
        source.config()?.context_template,
        settings.settings.value.context_template
      )
    ),
    openHover: (object, event, options) => {
      if (!source.preview()) {
        hover.open(object, event, options)
      }
    },
    openSubtreeHover: (object, state, event) => {
      if (!source.preview()) {
        hover.open(object, event, { stateOverride: state })
      }
    },
    openContext: (object, event) => {
      // An object the operator may not see has nothing to offer them.
      if (source.stateOf(object.id)?.state === 'NO_PERMISSION') {
        return
      }
      context.object = object
      context.x = event.pageX
      context.y = event.pageY
      context.visible = true
    },
    close
  }
}
