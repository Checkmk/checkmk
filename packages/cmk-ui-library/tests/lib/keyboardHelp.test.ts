/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import {
  type KeyboardHelpEntry,
  comboKey,
  comboLabels,
  getKeyboardHelp,
  highlightCombo,
  highlightedCombo,
  registerKeyboardHelp,
  subscribeKeyboardHelp,
  useKeyboardHints,
  useWidgetKeys
} from 'cmk-ui-library/lib/keyboardHelp'
import { expect, test } from 'vitest'
import { effectScope } from 'vue'

function t(value: string): TranslatedString {
  return value as TranslatedString
}

/** The registry is a page-lifetime singleton. */
function entriesOf(scope: string): KeyboardHelpEntry[] {
  return getKeyboardHelp().filter((entry) => entry.scope === scope)
}

test('registered entries are listed until they are unregistered', () => {
  const entry: KeyboardHelpEntry = {
    kind: 'shortcut',
    scope: t('Registry'),
    combo: ['Ctrl', 'k'],
    description: t('Open search')
  }
  const unregister = registerKeyboardHelp([entry])

  expect(entriesOf('Registry')).toEqual([entry])

  unregister()
  expect(entriesOf('Registry')).toEqual([])
})

test('subscribers hear about registrations and removals once each', () => {
  let notifications = 0
  const unsubscribe = subscribeKeyboardHelp(() => {
    notifications += 1
  })

  const unregister = registerKeyboardHelp([
    { kind: 'shortcut', scope: t('Subscribers'), combo: ['a'], description: undefined }
  ])
  unregister()
  unregister()

  expect(notifications).toBe(2)
  unsubscribe()
})

test('widget keys are released together with the effect scope which declared them', () => {
  const scope = effectScope()
  scope.run(() => {
    useWidgetKeys(t('Switch'), [{ combo: [' '], description: t('Toggle') }])
  })

  expect(entriesOf('Switch')).toEqual([
    { kind: 'widget', scope: 'Switch', combo: [' '], description: 'Toggle' }
  ])

  scope.stop()
  expect(entriesOf('Switch')).toEqual([])
})

test('hints are sentences without a combo of their own', () => {
  const scope = effectScope()
  scope.run(() => {
    useKeyboardHints(t('All hosts'), [t('Press [/] to search the table')])
  })

  expect(entriesOf('All hosts')).toEqual([
    { kind: 'hint', scope: 'All hosts', combo: [], description: 'Press [/] to search the table' }
  ])
  scope.stop()
})

test('combo labels use the key cap symbols and short names', () => {
  expect(
    comboLabels([
      'Ctrl',
      'Shift',
      'Alt',
      'ArrowDown',
      'Enter',
      'Backspace',
      ' ',
      'Escape',
      'PageUp'
    ])
  ).toEqual(['Ctrl', 'Shift', 'Alt', 'arrow-down', 'enter', 'backspace', 'Space', 'Esc', 'PgUp'])
  expect(comboLabels(['k', '/', 'F5', 'Space'])).toEqual(['K', '/', 'F5', 'Space'])
})

test('the highlighted combination is kept in its label form, so hints and rows compare', () => {
  highlightCombo(['ctrl', 'ArrowDown'])
  expect(highlightedCombo.value).toBe(comboKey(['Ctrl', 'arrowdown']))

  highlightCombo(null)
  expect(highlightedCombo.value).toBeNull()
})
