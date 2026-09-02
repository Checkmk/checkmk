/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Resolved colour values for the parts of a map that paint outside CSS.
 *
 * Almost everything a map draws is styled in CSS, or through an SVG ``style``
 * binding, and reads the shared tokens directly. A canvas cannot: it needs a
 * real colour value, and a fresh one whenever the operator switches theme.
 * Resolving the tokens once per map view — rather than once per graph — keeps
 * it to a single theme observer no matter how many graphs a map carries, and
 * every painter reads the same values, so they agree by construction.
 *
 * ``MapView`` declares the map-local properties and provides the palette; the
 * monitoring-state colours come from the shared ``--color-state-*`` tokens.
 */
import { useTheme } from 'cmk-ui-library/lib/useTheme'
import {
  type InjectionKey,
  type Ref,
  type ShallowRef,
  computed,
  inject,
  provide,
  ref,
  watch
} from 'vue'

import { stateColorProperty } from '@/maps/utils/stateColors'

/** How many ``--maps-map-view-series-N`` properties the map view declares. */
const SERIES_SLOTS = 8

export interface MapPalette {
  /** Fallback graph series colours, for metrics the registry has no colour for. */
  series: string[]
  /** Colour of a monitoring state. */
  state: (state: string | undefined) => string
  /** The unfilled part of a utilisation ring. */
  gaugeTrack: string
}

/**
 * Painters fall back to the inherited colour where the properties did not
 * resolve — outside a map view, or in a test environment without styles. A
 * missing provider is then a visual degradation, never a crash.
 */
const INHERIT = 'currentColor'

const FALLBACK: MapPalette = { series: [], state: () => INHERIT, gaugeTrack: INHERIT }

const MAP_PALETTE: InjectionKey<Ref<MapPalette>> = Symbol('maps-map-palette')

function readPalette(element: HTMLElement | null): MapPalette {
  if (!element) {
    return FALLBACK
  }
  const style = getComputedStyle(element)
  const read = (property: string): string => style.getPropertyValue(property).trim()
  return {
    series: Array.from({ length: SERIES_SLOTS }, (_unused, slot) =>
      read(`--maps-map-view-series-${slot + 1}`)
    ).filter((color) => color !== ''),
    state: (state) => read(stateColorProperty(state)) || INHERIT,
    gaugeTrack: read('--maps-map-view-gauge-track') || INHERIT
  }
}

/** Resolve the palette off ``root`` and hand it to everything below it. */
export function provideMapPalette(root: Readonly<ShallowRef<HTMLElement | null>>): void {
  const { theme } = useTheme()
  const palette = ref<MapPalette>(FALLBACK)
  watch(
    [root, theme],
    ([element]) => {
      palette.value = readPalette(element)
    },
    { immediate: true }
  )
  provide(MAP_PALETTE, palette)
}

/** The map view's palette, or inherited colours where there is no map view. */
export function useMapPalette(): Ref<MapPalette> {
  return inject(MAP_PALETTE, null) ?? computed(() => FALLBACK)
}
