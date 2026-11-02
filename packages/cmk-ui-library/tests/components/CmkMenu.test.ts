/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkMenu, { type CmkMenuItem, type CmkMenuLinkItem } from 'cmk-ui-library/components/CmkMenu'

function anItem(host: string, links: CmkMenuLinkItem['links'] = [{ title: 'Host', url: '#' }]) {
  return {
    color: '#3cc2ff',
    label: [
      { text: host, truncateOrder: 1 },
      { text: 'CPU load', truncateOrder: 2 },
      { text: 'Load average 1', bold: true }
    ],
    links
  } satisfies CmkMenuLinkItem
}

function itemsFor(count: number): CmkMenuItem[] {
  return Array.from({ length: count }, (_, index) => anItem(`host${index}`))
}

function expectItemsNamed(names: string[]): void {
  const items = screen.getAllByRole('menuitem')
  expect(items).toHaveLength(names.length)
  names.forEach((name, index) => expect(items[index]).toHaveAccessibleName(name))
}

async function openMenu(items: CmkMenuItem[], searchable = false): Promise<void> {
  render(CmkMenu, { props: { items, label: 'Contextual links', searchable } })
  await userEvent.click(screen.getByRole('button', { name: 'Contextual links' }))
  await screen.findByRole('menu', { name: 'Contextual links' })
}

test('opening the trigger shows every item, named by its whole label', async () => {
  await openMenu([anItem('web01'), anItem('db01')])

  expectItemsNamed(['web01 – CPU load – Load average 1', 'db01 – CPU load – Load average 1'])
})

test('search is shown from nine items on, even when not searchable', async () => {
  await openMenu(itemsFor(9))

  expect(screen.getByRole('searchbox', { name: 'Search' })).toBeInTheDocument()
})

test('search is hidden below nine items', async () => {
  await openMenu(itemsFor(8))

  expect(screen.queryByRole('searchbox')).not.toBeInTheDocument()
})

test('search is shown below nine items when searchable', async () => {
  await openMenu(itemsFor(2), true)

  expect(screen.getByRole('searchbox', { name: 'Search' })).toBeInTheDocument()
})

test('search keeps only the items whose label contains the query, ignoring case', async () => {
  await openMenu([anItem('web01'), anItem('db01')], true)

  await userEvent.type(screen.getByRole('searchbox', { name: 'Search' }), 'WEB')

  expectItemsNamed(['web01 – CPU load – Load average 1'])
})

test('reopening clears the query and shows every item again', async () => {
  await openMenu([anItem('web01'), anItem('db01')], true)
  await userEvent.type(screen.getByRole('searchbox', { name: 'Search' }), 'web')

  await userEvent.keyboard('{Escape}')
  await userEvent.click(screen.getByRole('button', { name: 'Contextual links' }))

  expect(await screen.findByRole('searchbox', { name: 'Search' })).toHaveValue('')
  expectItemsNamed(['web01 – CPU load – Load average 1', 'db01 – CPU load – Load average 1'])
})

test('search without a match says there are no results', async () => {
  await openMenu([anItem('web01')], true)

  await userEvent.type(screen.getByRole('searchbox', { name: 'Search' }), 'nothing')

  expect(screen.getByText('No results')).toBeInTheDocument()
})

test('an item with one link is that link, without a submenu', async () => {
  await openMenu([anItem('web01', [{ title: 'Host', url: '/host?name=web01' }])])

  const item = screen.getByRole('menuitem', { name: 'web01 – CPU load – Load average 1' })
  expect(item).toHaveAttribute('href', '/host?name=web01')
})

test('an item with several links opens a submenu of those links', async () => {
  await openMenu([
    anItem('web01', [
      { title: 'Host', url: '/host?name=web01' },
      { title: 'Service', url: '/service?name=web01' }
    ])
  ])

  await userEvent.click(screen.getByRole('menuitem', { name: 'web01 – CPU load – Load average 1' }))

  expect(await screen.findByRole('menuitem', { name: 'Host' })).toHaveAttribute(
    'href',
    '/host?name=web01'
  )
  expect(screen.getByRole('menuitem', { name: 'Service' })).toHaveAttribute(
    'href',
    '/service?name=web01'
  )
})

test('an open submenu follows reordered links, even when two share a URL', async () => {
  const links = [
    { title: 'Host', url: '/host' },
    { title: 'Service', url: '#' },
    { title: 'Graph', url: '#' },
    { title: 'Docs', url: '/docs' }
  ] satisfies CmkMenuLinkItem['links']
  const { rerender } = render(CmkMenu, {
    props: { items: [anItem('web01', links)], label: 'Contextual links' }
  })
  await userEvent.click(screen.getByRole('button', { name: 'Contextual links' }))
  await userEvent.click(screen.getByRole('menuitem', { name: 'web01 – CPU load – Load average 1' }))
  await screen.findByRole('menuitem', { name: 'Host' })

  await rerender({ items: [anItem('web01', [...links].reverse() as CmkMenuLinkItem['links'])] })

  expect(
    screen
      .getAllByRole('menuitem', { name: /^(Host|Service|Graph|Docs)$/ })
      .map((link) => link.textContent)
  ).toEqual(['Docs', 'Graph', 'Service', 'Host'])
})

test('a line 2 part renders apart from line 1, without a separator in between', async () => {
  const item: CmkMenuLinkItem = anItem('web01')
  item.label[2] = { text: 'Load average 1', bold: true, line: 2 }
  await openMenu([item])

  expect(screen.getByText('web01').parentElement).toHaveTextContent(/^web01 – CPU load$/)
  expect(screen.getByText('Load average 1').parentElement).toHaveTextContent(/^Load average 1$/)
})

test('a two-line item is named by its lines in display order, however its parts are listed', async () => {
  const item: CmkMenuLinkItem = anItem('web01')
  item.label = [
    { text: 'Load average 1', bold: true, line: 2 },
    { text: 'web01', truncateOrder: 1 },
    { text: 'CPU load', truncateOrder: 2 }
  ]
  await openMenu([item])

  expectItemsNamed(['web01 – CPU load – Load average 1'])
})

function valueItem(title: string, value: string): CmkMenuItem {
  return { label: [{ text: title }], value }
}

test('selecting a value item emits its value instead of navigating', async () => {
  const onSelect = vi.fn()
  render(CmkMenu, {
    props: {
      items: [
        valueItem('Custom graph 1', 'custom_graph_1'),
        valueItem('Custom graph 2', 'custom_graph_2')
      ],
      label: 'Clone custom graph',
      onSelect
    }
  })
  await userEvent.click(screen.getByRole('button', { name: 'Clone custom graph' }))

  const item = await screen.findByRole('menuitem', { name: 'Custom graph 2' })
  expect(item).not.toHaveAttribute('href')
  await userEvent.click(item)

  expect(onSelect).toHaveBeenCalledWith('custom_graph_2')
  expect(screen.queryByRole('menu')).not.toBeInTheDocument()
})

test('a trigger with text is named by its text', () => {
  render(CmkMenu, {
    props: { items: [], label: 'Custom graphs', triggerText: 'Clone custom graph' }
  })

  const trigger = screen.getByRole('button', { name: 'Clone custom graph' })
  expect(trigger).toHaveTextContent('Clone custom graph')
  expect(trigger).toHaveAttribute('title', '')
})

test('the trigger keeps its text after a value is selected', async () => {
  render(CmkMenu, {
    props: {
      items: [valueItem('Custom graph 1', 'custom_graph_1')],
      label: 'Custom graphs',
      triggerText: 'Clone custom graph'
    }
  })

  await userEvent.click(screen.getByRole('button', { name: 'Clone custom graph' }))
  await userEvent.click(await screen.findByRole('menuitem', { name: 'Custom graph 1' }))

  expect(screen.getByRole('button', { name: 'Clone custom graph' })).toHaveTextContent(
    'Clone custom graph'
  )
})

test('the default trigger is icon-only without text', () => {
  render(CmkMenu, { props: { items: [], label: 'Contextual links' } })

  expect(screen.getByRole('button', { name: 'Contextual links' })).toHaveTextContent('')
})

test('the search field takes the given placeholder', async () => {
  render(CmkMenu, {
    props: {
      items: [valueItem('Custom graph 1', 'custom_graph_1')],
      label: 'Clone custom graph',
      searchable: true,
      searchPlaceholder: 'Search custom graphs ...'
    }
  })
  await userEvent.click(screen.getByRole('button', { name: 'Clone custom graph' }))

  expect(
    await screen.findByRole('searchbox', { name: 'Search custom graphs ...' })
  ).toHaveAttribute('placeholder', 'Search custom graphs ...')
})
