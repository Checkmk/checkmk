/**
 * Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { GraphOptionUnitCustomNotationWithSymbol } from 'cmk-shared-typing/typescript/graph_designer'

type NotationType = GraphOptionUnitCustomNotationWithSymbol['type'] | 'time'

export function unitSymbolHasError(
  unitType: string,
  notation: NotationType,
  symbol: string
): boolean {
  if (unitType !== 'custom' || notation === 'time') {
    return false
  }
  return symbol.trim() === ''
}

export function unitDigitsHasError(unitType: string, digits: number): boolean {
  if (unitType !== 'custom') {
    return false
  }
  return typeof digits !== 'number' || digits < 0
}
