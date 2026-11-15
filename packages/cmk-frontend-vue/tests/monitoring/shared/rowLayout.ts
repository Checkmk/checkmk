/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { screen } from '@testing-library/vue'

/** The column id of the cell under each named header, in the first row of the table. */
export function columnIdsUnderHeaders(names: readonly string[]): Record<string, string | null> {
  const headers = screen.getAllByRole('columnheader')
  const cells = [...screen.getAllByRole('row')[1]!.querySelectorAll('[data-column-id]')]
  if (cells.length !== headers.length) {
    throw new Error(`the row has ${cells.length} cells under ${headers.length} headers`)
  }
  return Object.fromEntries(
    names.map((name) => [
      name,
      cells[headers.indexOf(screen.getByRole('columnheader', { name }))]!.getAttribute(
        'data-column-id'
      )
    ])
  )
}
