/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, within } from '@testing-library/vue'
import UclSearch from '@ucl/_ucl/components/UclSearch.vue'

// UclNavPage (rendered for each match) uses <RouterLink>; stub it as a plain
// anchor so the search results can render without a full router instance.
const renderOptions = {
  stubs: {
    RouterLink: {
      props: ['to'],
      template: '<a :href="to"><slot /></a>'
    }
  }
}

test('renders search input', () => {
  render(UclSearch)
  screen.getByPlaceholderText('Search...')
})

test('lists matching pages for a query (case-insensitive)', async () => {
  render(UclSearch, { global: renderOptions })
  const input = screen.getByPlaceholderText('Search...')

  // Lower-case query must still match the "CmkButton" page from the real nav tree.
  await fireEvent.update(input, 'cmkbutton')

  const results = screen.getByRole('list')
  expect(within(results).queryByText('No results found')).toBeNull()
  const links = within(results).getAllByRole('link')
  expect(links.length).toBeGreaterThan(0)
  expect(links.some((l) => l.textContent?.includes('CmkButton'))).toBe(true)
})

test('only lists pages whose name contains the query', async () => {
  render(UclSearch, { global: renderOptions })
  const input = screen.getByPlaceholderText('Search...')

  await fireEvent.update(input, 'CmkColorPicker')

  const links = within(screen.getByRole('list')).getAllByRole('link')
  expect(links.map((l) => l.textContent?.trim())).toEqual(['CmkColorPicker'])
})

test('shows no results message when query matches nothing', async () => {
  render(UclSearch)
  const input = screen.getByPlaceholderText('Search...')

  await fireEvent.update(input, 'xyznotfound12345')

  screen.getByText('No results found')
})

test('does not show results list when query is empty', () => {
  render(UclSearch)

  expect(screen.queryByText('No results found')).toBeNull()
})

test('clears results when input is emptied', async () => {
  render(UclSearch)
  const input = screen.getByPlaceholderText('Search...')

  await fireEvent.update(input, 'xyznotfound12345')
  await fireEvent.update(input, '')

  expect(screen.queryByText('No results found')).toBeNull()
})

test('arrow down in the input focuses the first result', async () => {
  render(UclSearch, { global: renderOptions })
  const input = screen.getByPlaceholderText('Search...')
  await fireEvent.update(input, 'cmk')

  await fireEvent.keyDown(input, { key: 'ArrowDown' })

  const links = within(screen.getByRole('list')).getAllByRole('link')
  expect(document.activeElement).toBe(links[0])
})

test('arrow down on a result focuses the next result', async () => {
  render(UclSearch, { global: renderOptions })
  await fireEvent.update(screen.getByPlaceholderText('Search...'), 'cmk')
  const links = within(screen.getByRole('list')).getAllByRole('link')
  links[0]!.focus()

  await fireEvent.keyDown(links[0]!, { key: 'ArrowDown' })

  expect(document.activeElement).toBe(links[1])
})

test('arrow up on the first result focuses the input', async () => {
  render(UclSearch, { global: renderOptions })
  const input = screen.getByPlaceholderText('Search...')
  await fireEvent.update(input, 'cmk')
  const firstLink = within(screen.getByRole('list')).getAllByRole('link')[0]!
  firstLink.focus()

  await fireEvent.keyDown(firstLink, { key: 'ArrowUp' })

  expect(document.activeElement).toBe(input)
})

test('arrow up on a later result focuses the previous result', async () => {
  render(UclSearch, { global: renderOptions })
  await fireEvent.update(screen.getByPlaceholderText('Search...'), 'cmk')
  const links = within(screen.getByRole('list')).getAllByRole('link')
  links[1]!.focus()

  await fireEvent.keyDown(links[1]!, { key: 'ArrowUp' })

  expect(document.activeElement).toBe(links[0])
})
