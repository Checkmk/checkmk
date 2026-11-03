/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import CmkMenu, { type CmkMenuItem } from 'cmk-ui-library/components/CmkMenu'

function anItem(host: string, links: CmkMenuItem['links'] = [{ title: 'Host', url: '#' }]) {
  return {
    color: '#3cc2ff',
    label: [
      { text: host, truncateOrder: 1 },
      { text: 'CPU load', truncateOrder: 2 },
      { text: 'Load average 1', bold: true }
    ],
    links
  } satisfies CmkMenuItem
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
  ] satisfies CmkMenuItem['links']
  const { rerender } = render(CmkMenu, {
    props: { items: [anItem('web01', links)], label: 'Contextual links' }
  })
  await userEvent.click(screen.getByRole('button', { name: 'Contextual links' }))
  await userEvent.click(screen.getByRole('menuitem', { name: 'web01 – CPU load – Load average 1' }))
  await screen.findByRole('menuitem', { name: 'Host' })

  await rerender({ items: [anItem('web01', [...links].reverse() as CmkMenuItem['links'])] })

  expect(
    screen
      .getAllByRole('menuitem', { name: /^(Host|Service|Graph|Docs)$/ })
      .map((link) => link.textContent)
  ).toEqual(['Docs', 'Graph', 'Service', 'Host'])
})
