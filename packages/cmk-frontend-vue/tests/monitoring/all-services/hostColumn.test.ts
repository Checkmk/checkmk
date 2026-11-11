/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { nextTick, ref, shallowRef } from 'vue'

import { useHostColumnWidth } from '@/monitoring/all-services/hostColumn'
import { SUBPIXEL_SLACK } from '@/monitoring/shared/components/MonitoringTableContext'
import { HOST_CELL_CHROME } from '@/monitoring/shared/components/cell/hostCell'
import type { TextWidth } from '@/monitoring/shared/components/timestampColumns'
import type { FetchState } from '@/monitoring/shared/services/MonitoringService'

interface Row {
  host_name: string
}

// Every glyph is 7px wide.
const monospaceWidth: TextWidth = (text) => text.length * 7

function rowsOf(...hosts: string[]): Row[] {
  return hosts.map((name) => ({ host_name: name }))
}

function hostWidthFor(nameLength: number, glyphWidth = 7): number {
  return nameLength * glyphWidth + SUBPIXEL_SLACK + HOST_CELL_CHROME
}

function listingOf(rows: Row[]) {
  return { items: shallowRef(rows), fetchState: ref<FetchState>('idle') }
}

test('the host column fits the longest host name next to its state tag', () => {
  const listing = listingOf(rowsOf('db-01', 'chassis-a-node1', 'web'))

  expect(useHostColumnWidth(listing, shallowRef(monospaceWidth)).value).toBe(hostWidthFor(15))
})

test('the host column grows when a refresh brings a longer host', async () => {
  const listing = listingOf(rowsOf('web'))
  const width = useHostColumnWidth(listing, shallowRef(monospaceWidth))

  listing.fetchState.value = 'background'
  listing.items.value = rowsOf('web', 'chassis-a-node1')
  listing.fetchState.value = 'idle'
  await nextTick()

  expect(width.value).toBe(hostWidthFor(15))
})

test('the host column keeps its width when a refresh drops its longest host', async () => {
  const listing = listingOf(rowsOf('chassis-a-node1', 'web'))
  const width = useHostColumnWidth(listing, shallowRef(monospaceWidth))

  listing.fetchState.value = 'background'
  listing.items.value = rowsOf('web')
  listing.fetchState.value = 'idle'
  await nextTick()

  expect(width.value).toBe(hostWidthFor(15))
})

test('the host column fits the rows of a new query anew', async () => {
  const listing = listingOf(rowsOf('chassis-a-node1', 'web'))
  const width = useHostColumnWidth(listing, shallowRef(monospaceWidth))

  listing.fetchState.value = 'foreground'
  listing.items.value = rowsOf('web')
  listing.fetchState.value = 'idle'
  await nextTick()

  expect(width.value).toBe(hostWidthFor(3))
})

test('the host column fits the rows of a new query anew though the font changes meanwhile', async () => {
  const listing = listingOf(rowsOf('chassis-a-node1'))
  const textWidth = shallowRef<TextWidth>(monospaceWidth)
  const width = useHostColumnWidth(listing, textWidth)

  listing.fetchState.value = 'foreground'
  textWidth.value = (text) => text.length * 9
  await nextTick()
  listing.items.value = rowsOf('web')
  listing.fetchState.value = 'idle'
  await nextTick()

  expect(width.value).toBe(hostWidthFor(3, 9))
})

test('the host column keeps its width on the refresh after a font change', async () => {
  const listing = listingOf(rowsOf('chassis-a-node1'))
  const textWidth = shallowRef<TextWidth>(monospaceWidth)
  const width = useHostColumnWidth(listing, textWidth)
  textWidth.value = (text) => text.length * 9
  await nextTick()

  listing.fetchState.value = 'background'
  listing.items.value = rowsOf('web')
  listing.fetchState.value = 'idle'
  await nextTick()

  expect(width.value).toBe(hostWidthFor(15, 9))
})

test('a host name is measured once however many services and refreshes show it', async () => {
  const measured: string[] = []
  const countingWidth: TextWidth = (text) => {
    measured.push(text)
    return monospaceWidth(text)
  }
  const listing = listingOf(rowsOf('web', 'db', 'web', 'web'))
  useHostColumnWidth(listing, shallowRef(countingWidth))

  listing.items.value = rowsOf('db', 'web')
  await nextTick()

  expect(measured.sort()).toEqual(['db', 'web'])
})

test('a new query measures its host names anew rather than keeping those of earlier queries', async () => {
  const measured: string[] = []
  const countingWidth: TextWidth = (text) => {
    measured.push(text)
    return monospaceWidth(text)
  }
  const listing = listingOf(rowsOf('web'))
  useHostColumnWidth(listing, shallowRef(countingWidth))

  listing.fetchState.value = 'foreground'
  listing.items.value = rowsOf('web')
  listing.fetchState.value = 'idle'
  await nextTick()

  expect(measured).toEqual(['web', 'web'])
})

test('the host column follows the font once it changes', async () => {
  const textWidth = shallowRef<TextWidth>(monospaceWidth)
  const width = useHostColumnWidth(listingOf(rowsOf('web')), textWidth)

  textWidth.value = (text) => text.length * 9
  await nextTick()

  expect(width.value).toBe(hostWidthFor(3, 9))
})

test('the host column has no width while text cannot be measured', () => {
  expect(useHostColumnWidth(listingOf(rowsOf('web')), shallowRef(null)).value).toBeNull()
})
