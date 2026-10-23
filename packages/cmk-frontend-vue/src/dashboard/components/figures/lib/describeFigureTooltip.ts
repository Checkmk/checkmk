/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { FigureTooltipContent } from './FigureTooltip.vue'

/** A tooltip's content as one line, for screen readers that never see the tooltip. */
export function describeFigureTooltip(content: FigureTooltipContent): string {
  return [content.state, ...content.rows.map((row) => `${row.count} ${row.text}`)]
    .filter((part) => part !== null && part !== '')
    .join(', ')
}
