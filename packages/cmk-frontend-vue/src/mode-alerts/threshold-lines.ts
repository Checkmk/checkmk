/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { HorizontalLine } from '@/graphing/components/TimeSeriesGraph'
import type { LevelsValue, ThresholdsValue } from '@/mode-alerts/types'

export interface LevelColors {
  warning: string
  critical: string
}

export interface LevelTitles {
  warning: string
  critical: string
}

export interface ThresholdLineTitles {
  upper: LevelTitles
  lower: LevelTitles
}

// Predictive levels move with the prediction, so they have no line to draw.
function fixedLevels(value: LevelsValue | undefined): {
  warning: number | ''
  critical: number | ''
} {
  if (value?.[0] !== 'fixed') {
    return { warning: '', critical: '' }
  }
  const [warning, critical] = value[1]
  return { warning, critical }
}

export function thresholdLines(
  thresholds: ThresholdsValue,
  unit: HorizontalLine['unit'],
  colors: LevelColors,
  titles: ThresholdLineTitles
): HorizontalLine[] {
  const lines: HorizontalLine[] = []
  for (const bound of ['upper', 'lower'] as const) {
    const levels = fixedLevels(thresholds[`${bound}_levels`])
    for (const level of ['warning', 'critical'] as const) {
      const value = levels[level]
      if (value !== '') {
        lines.push({
          name: `alert_${bound}_${level}`,
          title: titles[bound][level],
          color: colors[level],
          value,
          unit
        })
      }
    }
  }
  return lines
}
