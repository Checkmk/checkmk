/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { ColumnDef } from '@tanstack/vue-table'
import { type ComputedRef, type Ref, computed, shallowRef, watch } from 'vue'

import { longestTimestampShape } from '@/monitoring/shared/formatTimestamp'
import type { DisplayOptions, TimestampFormatId } from '@/monitoring/shared/types'

import { CELL_PADDING } from './MonitoringTableContext'

export type TextWidth = (text: string) => number

const DIGITS = '0123456789'

const FORMATS_SHOWING_AGES: ReadonlySet<TimestampFormatId> = new Set(['rel', 'mixed', 'both'])

/**
 * Measures text in the font of the table's cells, read from a probe cell within `reference`, which
 * inherits it the same way. Null where the browser can't measure text, as in jsdom.
 */
function cellTextWidth(reference: HTMLElement): TextWidth | null {
  const context = document.createElement('canvas').getContext('2d')
  if (!context) {
    return null
  }
  const probe = document.createElement('table')
  reference.append(probe)
  const style = getComputedStyle(probe.insertRow().insertCell())
  context.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`
  const letterSpacing = parseFloat(style.letterSpacing) || 0
  probe.remove()
  return (text) => context.measureText(text).width + text.length * letterSpacing
}

/**
 * Measures text in the font of the table's cells within `reference`, once it is mounted and anew
 * once its web font has arrived.
 */
export function useCellTextWidth(
  reference: Readonly<Ref<HTMLElement | null>>
): Readonly<Ref<TextWidth | null>> {
  const textWidth = shallowRef<TextWidth | null>(null)
  const measure = (): void => {
    textWidth.value = reference.value ? cellTextWidth(reference.value) : null
  }
  watch(reference, measure, { immediate: true, flush: 'post' })
  if ('fonts' in document) {
    void document.fonts.ready.then(measure)
  }
  return textWidth
}

/**
 * The width a timestamp column needs for the longest text its Timestamp Format can render, without
 * looking at the rows. The header can still widen the column. Null while text can't be measured.
 */
export function useTimestampColumnWidth(
  displayOptions: () => DisplayOptions,
  textWidth: Readonly<Ref<TextWidth | null>>
): ComputedRef<number | null> {
  return computed(() => {
    const measure = textWidth.value
    if (!measure) {
      return null
    }
    // The shape has every digit as `0`, but with proportional digits another one may be wider.
    const digit = [...DIGITS].reduce((widest, candidate) =>
      measure(candidate) > measure(widest) ? candidate : widest
    )
    const shape = longestTimestampShape(displayOptions())
    // A pixel to spare, so a sub-pixel difference between canvas and DOM layout doesn't wrap the
    // text's last glyph.
    return Math.ceil(measure(shape.replaceAll('0', digit))) + 1 + CELL_PADDING
  })
}

/**
 * Adapts each timestamp column to how its Timestamp Format shows it: fixed at `width`, or at what
 * its header needs if that is more, and filtered by duration where it shows ages. Without a `width`,
 * the column keeps its own sizes.
 */
export function timestampColumnsAsShown<T>(
  columns: ColumnDef<T>[],
  timestampFormat: TimestampFormatId,
  width: number | null
): ColumnDef<T>[] {
  return columns.map((column) => {
    const filter = column.meta?.filter
    if (filter?.type !== 'date-time-range') {
      return column
    }
    return {
      ...column,
      ...(width !== null && { minSize: width, maxSize: width }),
      meta: {
        ...column.meta,
        fitHeader: true,
        filter: FORMATS_SHOWING_AGES.has(timestampFormat)
          ? { type: 'duration', field: filter.field }
          : filter
      }
    }
  })
}
