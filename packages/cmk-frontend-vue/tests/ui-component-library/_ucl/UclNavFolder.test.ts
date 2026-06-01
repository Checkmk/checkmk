/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import UclNavFolder from '@ucl/_ucl/components/UclNavFolder.vue'
import type { NavFolder, NavPage } from '@ucl/_ucl/composables/useNavigation'
import { defineComponent, ref } from 'vue'

function makeFolder(overrides: Partial<NavFolder> = {}): NavFolder {
  return {
    type: 'folder',
    name: 'Components',
    path: '/Components',
    isOpen: ref(false),
    children: [],
    ...overrides
  }
}

function makePage(name: string): NavPage {
  return {
    type: 'page',
    name,
    path: `/Components/${name}`,
    component: defineComponent({ template: '<div/>' })
  }
}

test('renders folder name as button', () => {
  render(UclNavFolder, { props: { folder: makeFolder() } })
  screen.getByRole('button', { name: 'Components' })
})

test('is closed by default when isOpen is false', () => {
  render(UclNavFolder, { props: { folder: makeFolder({ isOpen: ref(false) }) } })
  expect(screen.getByRole('button', { name: 'Components' })).toHaveAttribute(
    'aria-expanded',
    'false'
  )
})

test('is open when isOpen is true', () => {
  render(UclNavFolder, { props: { folder: makeFolder({ isOpen: ref(true) }) } })
  expect(screen.getByRole('button', { name: 'Components' })).toHaveAttribute(
    'aria-expanded',
    'true'
  )
})

test('toggles open on click', async () => {
  const folder = makeFolder({ isOpen: ref(false) })
  render(UclNavFolder, { props: { folder } })
  const button = screen.getByRole('button', { name: 'Components' })

  await fireEvent.click(button)

  expect(button).toHaveAttribute('aria-expanded', 'true')
})

test('toggles closed again on second click', async () => {
  const folder = makeFolder({ isOpen: ref(false) })
  render(UclNavFolder, { props: { folder } })
  const button = screen.getByRole('button', { name: 'Components' })

  await fireEvent.click(button)
  await fireEvent.click(button)

  expect(button).toHaveAttribute('aria-expanded', 'false')
})

test('hides children when closed', () => {
  const folder = makeFolder({
    isOpen: ref(false),
    children: [makePage('CmkButton')]
  })
  render(UclNavFolder, { props: { folder } })

  expect(screen.queryByText('CmkButton')).toBeNull()
})

test('button has ucl-nav-folder class for focus-visible styling', () => {
  render(UclNavFolder, { props: { folder: makeFolder() } })
  const button = screen.getByRole('button', { name: 'Components' })
  expect(button).toHaveClass('ucl-nav-folder')
})
