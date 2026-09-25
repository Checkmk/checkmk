/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import {
  type KeyboardHelpEntry,
  highlightCombo,
  highlightedCombo,
  registerKeyboardHelp
} from 'cmk-ui-library/lib/keyboardHelp'
import { afterEach, expect, test } from 'vitest'
import { nextTick } from 'vue'

import KeyboardCheatSheet from '@/lib/keyboard-cheat-sheet/KeyboardCheatSheet.vue'

function t(value: string): TranslatedString {
  return value as TranslatedString
}

const SCOPE = t('Test scope')
const ALL_KINDS = ['shortcut', 'widget', 'hint'] as const
const VISIBLE = 'lib-keyboard-cheat-sheet--visible'
const ENTRY: KeyboardHelpEntry = {
  kind: 'shortcut',
  scope: SCOPE,
  combo: ['Ctrl', 'k'],
  description: t('Open search')
}

let unregister: (() => void) | null = null

/** The tracker is a page-lifetime singleton. */
afterEach(() => {
  unregister?.()
  unregister = null
  highlightCombo(null)
  releaseAlt()
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
  localStorage.clear()
})

function pressAltK(): void {
  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', altKey: true }))
  window.dispatchEvent(new KeyboardEvent('keyup', { key: 'k', altKey: true }))
}

function releaseAlt(): void {
  window.dispatchEvent(new KeyboardEvent('keyup', { key: 'Alt', altKey: false }))
}

function sheet(): HTMLElement {
  return document.querySelector('.lib-keyboard-cheat-sheet') as HTMLElement
}

async function show(
  entries: KeyboardHelpEntry[],
  kinds: readonly KeyboardHelpEntry['kind'][] = ALL_KINDS
): Promise<void> {
  unregister = registerKeyboardHelp(entries)
  render(KeyboardCheatSheet, { props: { kinds } })
  pressAltK()
  await nextTick()
}

test('lists a shortcut under its scope with one key cap per key', async () => {
  await show([ENTRY])

  expect(sheet()).toHaveClass(VISIBLE)
  expect(screen.getByText('Open search')).toBeInTheDocument()
  expect(screen.getByText('Test scope')).toBeInTheDocument()
  expect(screen.getByText('Ctrl')).toBeInTheDocument()
  expect(screen.getByText('K')).toBeInTheDocument()
})

test('merges alternative combinations of the same action into one row', async () => {
  await show([
    { kind: 'shortcut', scope: SCOPE, combo: ['Ctrl', '/'], description: t('Toggle sidebar') },
    {
      kind: 'shortcut',
      scope: SCOPE,
      combo: ['Ctrl', 'Shift', '/'],
      description: t('Toggle sidebar')
    }
  ])

  expect(screen.getAllByText('Toggle sidebar')).toHaveLength(1)
  expect(screen.getAllByText('Ctrl')).toHaveLength(2)
  expect(screen.getByText('Shift')).toBeInTheDocument()
})

test('marks a shortcut without description as undocumented', async () => {
  await show([{ kind: 'shortcut', scope: SCOPE, combo: ['Ctrl', 'Enter'], description: undefined }])

  expect(screen.getByText('undocumented')).toBeInTheDocument()
})

test('renders the bracketed keys of a hint as key caps', async () => {
  await show([
    { kind: 'hint', scope: SCOPE, combo: [], description: t('Press [Enter] on a host name') }
  ])

  expect(screen.getByText('↵')).toBeInTheDocument()
  expect(screen.getByText(/on a host name/)).toBeInTheDocument()
})

test('shows only the kinds it was asked for', async () => {
  await show(
    [
      { kind: 'shortcut', scope: SCOPE, combo: ['/'], description: t('Focus search') },
      { kind: 'widget', scope: SCOPE, combo: [' '], description: t('Toggle') }
    ],
    ['shortcut']
  )

  expect(screen.getByText('Focus search')).toBeInTheDocument()
  expect(screen.queryByText('Toggle')).not.toBeInTheDocument()
})

test('splits a combination into modifiers, the plus and the key, and leaves the modifiers of a single key empty', async () => {
  await show([
    ENTRY,
    { kind: 'shortcut', scope: SCOPE, combo: ['Escape'], description: t('Close menu') }
  ])

  const modifiers = document.querySelectorAll('.lib-keyboard-cheat-sheet__modifiers')
  const keys = document.querySelectorAll('.lib-keyboard-cheat-sheet__keys')
  expect(modifiers[0]).toHaveTextContent('Ctrl')
  expect(keys[0]).toHaveTextContent('K')
  expect(modifiers[1]).toHaveTextContent('')
  expect(keys[1]).toHaveTextContent('Esc')
  expect(document.querySelectorAll('.lib-keyboard-cheat-sheet__plus')[0]).toHaveTextContent('+')
})

test('gives a tall group a column of its own and leaves no column empty', async () => {
  const tall: KeyboardHelpEntry[] = Array.from({ length: 12 }, (_unused, index) => ({
    kind: 'shortcut',
    scope: t('Tall'),
    combo: [`${index}`],
    description: t(`Row ${index}`)
  }))
  await show([
    ...tall,
    { kind: 'shortcut', scope: t('Short one'), combo: ['a'], description: t('One') },
    { kind: 'shortcut', scope: t('Short two'), combo: ['b'], description: t('Two') }
  ])

  const columns = document.querySelectorAll('.lib-keyboard-cheat-sheet__column')
  expect(columns).toHaveLength(3)
  expect(columns[0]?.querySelectorAll('section')).toHaveLength(1)
  expect(columns[0]).toHaveTextContent('Tall')
})

test('the main menu heads the first column, whatever its size', async () => {
  const tall: KeyboardHelpEntry[] = Array.from({ length: 12 }, (_unused, index) => ({
    kind: 'shortcut',
    scope: t('Search'),
    combo: [`${index}`],
    description: t(`Row ${index}`)
  }))
  await show([
    ...tall,
    { kind: 'shortcut', scope: t('Main menu'), combo: ['Alt', 'm'], description: t('Monitor') },
    { kind: 'shortcut', scope: t('Sidebar'), combo: ['Ctrl', '/'], description: t('Toggle') }
  ])

  const columns = document.querySelectorAll('.lib-keyboard-cheat-sheet__column')
  expect(columns[0]?.querySelector('section')).toHaveTextContent('Main menu')
})

test('goes away when Alt is released after a single Alt+K', async () => {
  await show([ENTRY])
  releaseAlt()
  await nextTick()

  expect(sheet()).not.toHaveClass(VISIBLE)
})

test('Alt+K+K pins it, Esc lets it go', async () => {
  await show([ENTRY])
  pressAltK()
  releaseAlt()
  await nextTick()
  expect(sheet()).toHaveClass(VISIBLE)

  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
  await nextTick()
  expect(sheet()).not.toHaveClass(VISIBLE)
})

test('one more Alt+K lets a pinned sheet go', async () => {
  await show([ENTRY])
  pressAltK()
  releaseAlt()
  await nextTick()
  expect(sheet()).toHaveClass(VISIBLE)

  pressAltK()
  releaseAlt()
  await nextTick()
  expect(sheet()).not.toHaveClass(VISIBLE)
})

test('the pin keeps the sheet up once Alt is released, and lets it go again', async () => {
  await show([ENTRY])

  await fireEvent.click(screen.getByRole('button', { name: 'Pin the cheat sheet' }))
  releaseAlt()
  await nextTick()
  expect(sheet()).toHaveClass(VISIBLE)

  await fireEvent.click(screen.getByRole('button', { name: 'Unpin the cheat sheet' }))
  await nextTick()
  expect(sheet()).not.toHaveClass(VISIBLE)
})

function row(description: string): HTMLElement {
  return screen.getByText(description).closest('.lib-keyboard-cheat-sheet__row') as HTMLElement
}

test('a key hint under the pointer highlights its row', async () => {
  await show([ENTRY])

  highlightCombo(['Ctrl', 'k'])
  await nextTick()

  expect(row('Open search')).toHaveClass('lib-keyboard-cheat-sheet__row--highlighted')
})

test('pinned, a row under the pointer highlights its key hint; held, it does not', async () => {
  await show([ENTRY])

  await fireEvent.mouseEnter(row('Open search'))
  expect(highlightedCombo.value).toBeNull()

  pressAltK()
  releaseAlt()
  await nextTick()
  expect(sheet()).toHaveClass('lib-keyboard-cheat-sheet--pinned')

  await fireEvent.mouseEnter(row('Open search'))
  expect(highlightedCombo.value).toBe('Ctrl+K')
  await fireEvent.mouseLeave(row('Open search'))
  expect(highlightedCombo.value).toBeNull()
})
