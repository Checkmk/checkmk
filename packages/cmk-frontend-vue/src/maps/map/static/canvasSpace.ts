/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

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
