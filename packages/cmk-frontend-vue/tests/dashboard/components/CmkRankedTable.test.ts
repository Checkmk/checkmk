/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, within } from '@testing-library/vue'
import { nextTick } from 'vue'

import CmkRankedTable from '@/dashboard/components/CmkRankedTable/CmkRankedTable.vue'
import type {
  RankedTableCell,
  RankedTableColumn,
  RankedTableRow
} from '@/dashboard/components/CmkRankedTable/types'

const COLUMNS: RankedTableColumn[] = [
  { key: 'host', title: 'Host', render: 'text', bar: false },
  { key: 'services', title: 'Services', render: 'count', bar: false },
  { key: 'problems', title: 'Problems', render: 'count', bar: true }
]

const ROWS: RankedTableRow[] = [
  { host: 'B', services: 5, problems: 100 },
  { host: 'A', services: 10, problems: 40 },
  { host: 'C', services: 1, problems: 20 }
]

const TWO_DESTINATIONS: RankedTableCell = {
  value: 'A',
  choices: [
    { title: 'Host', href: 'view.py?view_name=host' },
    { title: 'Services', href: 'view.py?view_name=host_services' }
  ]
}

function renderTable(rows: RankedTableRow[] = ROWS) {
  return render(CmkRankedTable, { props: { columns: COLUMNS, rows } })
}

test('renders a header per column and a row per data entry', () => {
  const { container } = renderTable()

  expect(container.querySelectorAll('.db-cmk-ranked-table__th')).toHaveLength(3)
  expect(container.querySelector('thead')).toHaveTextContent('Host')
  expect(container.querySelectorAll('tbody tr')).toHaveLength(3)
})

test('keeps the row order provided by the caller', () => {
  const { container } = renderTable()

  const firstCells = [...container.querySelectorAll('tbody tr')].map(
    (tr) => tr.querySelector('td')?.textContent
  )
  expect(firstCells).toEqual(['B', 'A', 'C'])
})

test('scales inline bars to the column max', () => {
  const { container } = renderTable()

  const fills = [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')]
  expect(fills.map((el) => el.style.width)).toEqual(['100%', '40%', '20%'])
})

test('scales bars against a fixed barRange, clamped to it', () => {
  const columns: RankedTableColumn[] = [
    { key: 'host', title: 'Host', render: 'text', bar: false },
    { key: 'value', title: 'Value', render: 'count', bar: true, barRange: [100, 200] }
  ]
  const { container } = render(CmkRankedTable, {
    props: {
      columns,
      rows: [
        { host: 'A', value: 150 },
        { host: 'B', value: 40 },
        { host: 'C', value: 500 }
      ]
    }
  })

  const fills = [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')]
  expect(fills.map((el) => el.style.width)).toEqual(['50%', '0%', '100%'])
})

test('fills the bar when the barRange has collapsed to a single value', () => {
  const columns: RankedTableColumn[] = [
    { key: 'host', title: 'Host', render: 'text', bar: false },
    { key: 'value', title: 'Value', render: 'count', bar: true, barRange: [42, 42] }
  ]
  const { container } = render(CmkRankedTable, {
    props: { columns, rows: [{ host: 'A', value: 42 }] }
  })

  const fill = container.querySelector<HTMLElement>('.db-cmk-ranked-table__bar-fill')
  expect(fill!.style.width).toBe('100%')
})

test("prefers a cell's formatted text over the column formatting", () => {
  const { container } = renderTable([
    { host: 'A', services: 1, problems: { value: 5, formatted: 'five' } }
  ])

  expect(container.querySelector('tbody td:last-child')).toHaveTextContent('five')
})

test('lets a cell override the bar color, and leaves others to the default', () => {
  const { container } = renderTable([
    { host: 'A', services: 1, problems: { value: 5, color: 'rgb(1, 2, 3)' } },
    { host: 'B', services: 1, problems: 2 }
  ])

  const fills = [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')]
  expect(fills[0]!.style.backgroundColor).toBe('rgb(1, 2, 3)')
  expect(fills[1]!.style.backgroundColor).toBe('')
})

test('renders a link for cells carrying an href', () => {
  const { container } = renderTable([
    { host: { value: 'A', href: 'view.py?view_name=host' }, services: 1, problems: 5 }
  ])

  const link = container.querySelector<HTMLAnchorElement>('tbody a')
  expect(link).not.toBeNull()
  expect(link!.getAttribute('href')).toBe('view.py?view_name=host')
  expect(link!).toHaveTextContent('A')
})

test('offers the full text of truncatable cells as a tooltip, but not of figures', () => {
  const host = 'node_webshop_i-020818453318b7c7.eu-central-1.compute.internal'
  const { getByRole, queryByTitle } = renderTable([
    { host: { value: host, href: 'view.py' }, services: 1234, problems: 5 }
  ])

  expect(getByRole('link')).toHaveAttribute('title', host)
  expect(queryByTitle('1234')).toBeNull()
})

test('offers several destinations of a cell through a menu', () => {
  const { getByRole } = renderTable([
    {
      host: TWO_DESTINATIONS,
      services: 1,
      problems: 5
    }
  ])

  expect(getByRole('button', { name: 'A' })).toHaveAttribute('aria-haspopup', 'menu')
})

test('marks only a cell with several destinations with the menu arrow', () => {
  const { container } = renderTable([
    {
      host: TWO_DESTINATIONS,
      services: 1,
      problems: 5
    },
    { host: { value: 'B', href: 'view.py?view_name=host' }, services: 1, problems: 2 }
  ])

  const arrows = [...container.querySelectorAll('tbody tr')].map(
    (row) => row.querySelectorAll('.db-contextual-link-anchor__arrow').length
  )
  expect(arrows).toEqual([1, 0])
})

test('marks the table busy while new rows are fetched', () => {
  const { getByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: ROWS, busy: true }
  })

  expect(getByRole('table')).toHaveAttribute('aria-busy', 'true')
})

test('shows as many loading rows as asked for, in place of the data', () => {
  const { getByRole, getAllByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: ROWS, placeholder: { kind: 'loading', rows: 5 } }
  })

  expect(getByRole('table')).toHaveAttribute('aria-busy', 'true')
  expect(getAllByRole('row').slice(1)).toHaveLength(5)
  expect(getByRole('table')).not.toHaveTextContent('B')
})

test('hides the faded stand-ins of an empty table but not its message', () => {
  const { queryByRole, getByText } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: [], placeholder: { kind: 'empty', rows: 3 } },
    slots: { empty: 'No data' }
  })

  expect(queryByRole('table')).toBeNull()
  expect(getByText('No data')).toBeVisible()
})

test('shows no stand-in rows for a negative row count', () => {
  const { getAllByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: [], placeholder: { kind: 'loading', rows: -1 } }
  })

  expect(getAllByRole('row')).toHaveLength(1)
})

test('numbers the rows in the order provided, under a "Rank" header', () => {
  const { getByRole, getAllByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: ROWS, showRank: true }
  })

  expect(getByRole('columnheader', { name: 'Rank' })).toHaveTextContent('#')
  const ranks = getAllByRole('row')
    .slice(1)
    .map((row) => row.querySelector('td')?.textContent?.trim())
  expect(ranks).toEqual(['1', '2', '3'])
})

test('shows no rank column unless asked for', () => {
  const { queryByRole } = renderTable()

  expect(queryByRole('columnheader', { name: 'Rank' })).toBeNull()
})

test('leaves the rank of loading rows blank', () => {
  const { getAllByRole } = render(CmkRankedTable, {
    props: {
      columns: COLUMNS,
      rows: ROWS,
      showRank: true,
      placeholder: { kind: 'loading', rows: 2 }
    }
  })

  const ranks = getAllByRole('row')
    .slice(1)
    .map((row) => row.querySelector('td')?.textContent)
  expect(ranks).toEqual(['', ''])
})

test('leaves a zero value without a bar but keeps a sliver of any other value', () => {
  const { container } = renderTable([
    { host: 'A', services: 1, problems: 1000 },
    { host: 'B', services: 1, problems: 1 },
    { host: 'C', services: 1, problems: 0 }
  ])

  const fills = [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')]
  expect(fills.map((el) => el.style.width)).toEqual(['100%', '2%', '0%'])
})

test('grows the bars of negative values from zero, by their size', () => {
  const { container } = renderTable([
    { host: 'A', services: 1, problems: -1 },
    { host: 'B', services: 1, problems: -10 }
  ])

  const fills = [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')]
  expect(fills.map((el) => el.style.width)).toEqual(['10%', '100%'])
})

test('hides the bars from assistive tech, so cells line up with the column headers', () => {
  const { getAllByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: ROWS, showRank: true }
  })

  const headers = getAllByRole('columnheader')
  for (const row of getAllByRole('row').slice(1)) {
    expect(within(row).getAllByRole('cell')).toHaveLength(headers.length)
  }
})

test("shows a linked value's unit after it", () => {
  const { getByRole } = renderTable([
    {
      host: 'A',
      services: 1,
      problems: { value: 87.3, formatted: '87.3', unit: '%', href: 'view.py' }
    }
  ])

  expect(getByRole('link')).toHaveTextContent('87.3 %')
})

test("shows a value's unit after it", () => {
  const { getAllByRole } = renderTable([
    { host: 'A', services: 1, problems: { value: 87.3, formatted: '87.3', unit: '%' } }
  ])

  expect(getAllByRole('cell').at(-1)).toHaveTextContent('87.3 %')
})

test('names the table by its label', () => {
  const { getByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: ROWS, label: 'Top 3: Problems' }
  })

  expect(getByRole('table', { name: 'Top 3: Problems' })).toBeInTheDocument()
})

test('names each row of a ranked table by its rank', () => {
  const { getAllByRole } = render(CmkRankedTable, {
    props: { columns: COLUMNS, rows: ROWS, showRank: true }
  })

  expect(
    getAllByRole('row')
      .slice(1)
      .map((row) => row.getAttribute('aria-label'))
  ).toEqual(['Rank 1', 'Rank 2', 'Rank 3'])
})

test('leaves the rows of an unranked table to be named by their cells', () => {
  const { getAllByRole } = renderTable()

  expect(getAllByRole('row').every((row) => !row.hasAttribute('aria-label'))).toBe(true)
})

describe('on a refresh', () => {
  const VALUE: RankedTableColumn = {
    key: 'value',
    title: 'Value',
    render: 'count',
    bar: true,
    barRange: [0, 100]
  }
  const COLUMNS_WITH_VALUE: RankedTableColumn[] = [
    { key: 'host', title: 'Host', render: 'text', bar: false },
    VALUE
  ]

  function entry(host: string, formatted: string, unit = '%'): RankedTableRow {
    return {
      host: { value: host, href: `view.py?host=${host}` },
      value: { value: Number(formatted) || 0, formatted, unit }
    }
  }

  const byHost = (row: RankedTableRow) => String((row.host as RankedTableCell).value)

  // The tween runs on animation frames; driving them by hand keeps the tests deterministic.
  let frames = new Map<number, FrameRequestCallback>()
  let nextFrameHandle = 0
  let now = 0

  beforeEach(() => {
    frames = new Map()
    nextFrameHandle = 0
    now = 0
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      frames.set(++nextFrameHandle, callback)
      return nextFrameHandle
    })
    vi.stubGlobal('cancelAnimationFrame', (handle: number) => frames.delete(handle))
    vi.spyOn(performance, 'now').mockImplementation(() => now)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    delete (Element.prototype as Partial<Element>).scrollIntoView
  })

  async function renderFrame(elapsedMs: number): Promise<void> {
    now += elapsedMs
    const pending = [...frames.values()]
    frames.clear()
    pending.forEach((callback) => callback(now))
    await nextTick()
  }

  function renderRefreshable(rows: RankedTableRow[]) {
    return render(CmkRankedTable, {
      props: { columns: COLUMNS_WITH_VALUE, rows, rowKey: byHost }
    })
  }

  function barWidths(container: Element): string[] {
    return [...container.querySelectorAll<HTMLElement>('.db-cmk-ranked-table__bar-fill')].map(
      (el) => el.style.width
    )
  }

  function shownValue(container: Element): string | undefined {
    const cell = container.querySelector('tbody td:last-child')!
    const counting = cell.querySelector('[aria-hidden="true"]')
    return (counting ?? cell.querySelector('.db-cmk-ranked-table__text'))?.textContent?.trim()
  }

  test('draws the first rows without animating', () => {
    const { container } = renderRefreshable([entry('A', '40')])

    expect(barWidths(container)).toEqual(['40%'])
  })

  test('starts a refresh from the bar and value that were shown', async () => {
    const { container, rerender } = renderRefreshable([entry('A', '40.0')])

    await rerender({ rows: [entry('A', '80.0')] })

    expect([barWidths(container), shownValue(container)]).toEqual([['40%'], '40.0'])
  })

  test('counts through the values in between, in the decimals of the new value', async () => {
    const { container, rerender } = renderRefreshable([entry('A', '40.0')])
    await rerender({ rows: [entry('A', '80.0')] })

    await renderFrame(100)

    expect(shownValue(container)).toMatch(/^(4[1-9]|[5-7]\d)\.\d$/)
  })

  test('ends a refresh on the given text and bar', async () => {
    const { container, rerender } = renderRefreshable([entry('A', '40.0')])
    await rerender({ rows: [entry('A', '80.0')] })

    await renderFrame(200)

    expect([barWidths(container), shownValue(container)]).toEqual([['80%'], '80.0 %'])
  })

  test('shows no value from before the refresh for a frame timed before its start', async () => {
    const { container, rerender } = renderRefreshable([entry('A', '40')])
    await rerender({ rows: [entry('A', '80')] })

    await renderFrame(-50)

    expect(shownValue(container)).toBe('40')
  })

  test('gives assistive tech only the final value while counting', async () => {
    const { container, getAllByRole, rerender } = renderRefreshable([entry('A', '40')])

    await rerender({ rows: [entry('A', '80')] })

    const valueCell = within(getAllByRole('cell').at(-1)!)
    const audible = { ignore: '[aria-hidden="true"]' }
    expect(valueCell.queryByText('40', audible)).toBeNull()
    expect(valueCell.getByText('80', audible)).toBeInTheDocument()
    expect(shownValue(container)).toBe('40')
  })

  test('counts from the old value as shown, with the decimals of either end', async () => {
    const { container, rerender } = renderRefreshable([entry('A', '40.5')])

    await rerender({ rows: [entry('A', '80')] })

    expect(shownValue(container)).toBe('40.5')
  })

  test('switches the value at once when its unit changes', async () => {
    const { container, rerender } = renderRefreshable([entry('A', '900', 'MB')])

    await rerender({ rows: [entry('A', '1.2', 'GB')] })

    expect(shownValue(container)).toBe('1.2 GB')
  })

  test('animates nothing when the reader prefers reduced motion', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    const { container, rerender } = renderRefreshable([entry('A', '40')])

    await rerender({ rows: [entry('A', '80')] })

    expect(barWidths(container)).toEqual(['80%'])
    expect(shownValue(container)).toBe('80 %')
  })

  test('keeps each row with its key when the ranking changes', async () => {
    const { container, rerender } = renderRefreshable([entry('A', '80'), entry('B', '40')])
    const rowOfA = container.querySelector('tbody tr')

    await rerender({ rows: [entry('B', '90'), entry('A', '30')] })

    expect(container.querySelectorAll('tbody tr')[1]).toBe(rowOfA)
    expect(barWidths(container)).toEqual(['40%', '80%'])
  })

  function stubScrolling() {
    // jsdom does no layout, so it has no scrolling either.
    const scrollIntoView = vi.fn()
    Element.prototype.scrollIntoView = scrollIntoView
    return scrollIntoView
  }

  test('keeps keyboard focus on the same host when the ranking changes', async () => {
    stubScrolling()
    const { getByRole, rerender } = renderRefreshable([entry('A', '80'), entry('B', '40')])
    getByRole('link', { name: 'B' }).focus()

    await rerender({ rows: [entry('B', '90'), entry('A', '30')] })

    expect(getByRole('link', { name: 'B' })).toHaveFocus()
  })

  // jsdom has no layout to scroll, so the call to scroll is all there is to observe.
  test('does not scroll to a row whose focus only followed it', async () => {
    const scrollIntoView = stubScrolling()
    const { getByRole, rerender } = renderRefreshable([entry('A', '80'), entry('B', '40')])
    getByRole('link', { name: 'B' }).focus()
    scrollIntoView.mockClear()

    await rerender({ rows: [entry('B', '90'), entry('A', '30')] })

    expect(scrollIntoView).not.toHaveBeenCalled()
  })

  test('hands the focus of a row that left to the row in its place', async () => {
    stubScrolling()
    const { getByRole, rerender } = renderRefreshable([entry('A', '80'), entry('B', '40')])
    getByRole('link', { name: 'B' }).focus()

    await rerender({ rows: [entry('A', '80'), entry('C', '30')] })

    expect(getByRole('link', { name: 'C' })).toHaveFocus()
  })
})
