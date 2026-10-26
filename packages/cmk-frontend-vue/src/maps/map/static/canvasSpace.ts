/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { BackgroundPosition, BackgroundStyle, MapConfig } from '@/maps/types/api'

export interface SpaceSize {
  width: number
  height: number
}

/**
 * The map's coordinate space extended, to the right or below, to the pane's
 * proportions, so that it fills the pane at one scale for both axes.
 */
export function spaceFillingPane(map: SpaceSize, pane: SpaceSize): SpaceSize {
  if (!pane.width || !pane.height || !map.width || !map.height) {
    return map
  }
  const paneRatio = pane.width / pane.height
  return paneRatio > map.width / map.height
    ? { width: map.height * paneRatio, height: map.height }
    : { width: map.width, height: map.width / paneRatio }
}

export interface BackgroundLayout {
  /** CSS ``background-size``, as percentages of the canvas. */
  size: string
  /** CSS ``background-position``, as percentages of the canvas. */
  position: string
  repeat: boolean
}

/**
 * Where the background image lands on the canvas, worked out in map units and
 * handed to CSS as percentages, so it holds at any zoom and window size and
 * stays registered with the objects.
 *
 * ``map`` is the map's own space, ``shown`` the space the canvas spans and
 * ``image`` the image's own size; without that size only stretching can be
 * laid out, so the image waits rather than flashing up stretched.
 */
export function backgroundLayout(
  style: BackgroundStyle,
  position: BackgroundPosition,
  map: SpaceSize,
  shown: SpaceSize,
  image: SpaceSize | null
): BackgroundLayout | null {
  let box: SpaceSize
  if (style === 'stretch') {
    box = map
  } else if (!image?.width || !image.height) {
    return null
  } else if (style === 'zoom') {
    const factor = Math.min(map.width / image.width, map.height / image.height)
    box = { width: image.width * factor, height: image.height * factor }
  } else {
    box = image
  }
  const align = (mapLength: number, shownLength: number, boxLength: number): number => {
    const offset = position === 'center' ? (mapLength - boxLength) / 2 : 0
    return shownLength === boxLength ? 0 : (offset / (shownLength - boxLength)) * 100
  }
  return {
    size: `${(box.width / shown.width) * 100}% ${(box.height / shown.height) * 100}%`,
    position: `${align(map.width, shown.width, box.width)}% ${align(map.height, shown.height, box.height)}%`,
    repeat: style === 'tile'
  }
}

/**
 * Whether the map is shown as an artboard centered in its pane, at its own
 * proportions, rather than filling the pane from the top left.
 */
export function isCentered(config: MapConfig, preview: boolean): boolean {
  return (
    !preview &&
    config.render_mode !== 'nagvis_classic' &&
    !!config.background_image &&
    config.background_position === 'center'
  )
}
