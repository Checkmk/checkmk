/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen } from '@testing-library/vue'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, test } from 'vitest'

import DynamicPresets from '@/graphing/GlobalTimePicker/private/DynamicPresets.vue'
import type { CustomPreset } from '@/graphing/GlobalTimePicker/private/useCustomPresets.ts'

const PRESETS: CustomPreset[] = [
  { id: 'p1', label: untranslated('Last 4 hours'), totalSeconds: 4 * 3600 },
  { id: 'p2', label: untranslated('Last 25 hours'), totalSeconds: 25 * 3600 }
]

/** In render order, skipping the `aria-hidden` measurement replica. */
function chipNames(container: Element): string[] {
  return Array.from(container.querySelectorAll<HTMLElement>('.graphing-dynamic-presets > button'))
    .filter((button) => button.hasAttribute('aria-pressed'))
    .map((button) => button.textContent!.trim())
}

function renderPresets(
  props: {
    activePresetId?: string | null
    includeCustomEntry?: boolean
    variant?: 'extended' | 'condensed'
  } = {}
) {
  const emitted: CustomPreset[] = []
  const view = render(DynamicPresets, {
    props: {
      presets: PRESETS,
      activePresetId: props.activePresetId ?? null,
      includeCustomEntry: props.includeCustomEntry ?? false,
      ...(props.variant ? { variant: props.variant } : {}),
      onApply: (preset: CustomPreset) => emitted.push(preset)
    }
  })
  return { ...view, emitted }
}

describe('DynamicPresets includeCustomEntry', () => {
  test('defaults to false: no "Custom range" entry is added', () => {
    const { container } = renderPresets()
    expect(chipNames(container)).toEqual(['Last 4 hours', 'Last 25 hours'])
  })

  test('false explicitly: still no "Custom range" entry', () => {
    const { container } = renderPresets({ includeCustomEntry: false })
    expect(chipNames(container)).toEqual(['Last 4 hours', 'Last 25 hours'])
  })

  test('true: appends a trailing "Custom range" entry', () => {
    const { container } = renderPresets({ includeCustomEntry: true })
    expect(chipNames(container)).toEqual(['Last 4 hours', 'Last 25 hours', 'Custom range'])
  })

  test('true and activePresetId null: the Custom chip shows pressed, the others do not', () => {
    renderPresets({ includeCustomEntry: true, activePresetId: null })
    expect(screen.getByRole('button', { name: 'Custom range' })).toHaveAttribute(
      'aria-pressed',
      'true'
    )
    expect(screen.getByRole('button', { name: 'Last 4 hours' })).toHaveAttribute(
      'aria-pressed',
      'false'
    )
  })

  test('true and a real preset active: the Custom chip shows unpressed', () => {
    renderPresets({ includeCustomEntry: true, activePresetId: 'p1' })
    expect(screen.getByRole('button', { name: 'Custom range' })).toHaveAttribute(
      'aria-pressed',
      'false'
    )
  })

  test('clicking the Custom chip emits apply with id null', async () => {
    const { emitted } = renderPresets({ includeCustomEntry: true })
    await fireEvent.click(screen.getByRole('button', { name: 'Custom range' }))
    expect(emitted).toEqual([{ id: null, label: untranslated('Custom range'), totalSeconds: 0 }])
  })
})

describe('DynamicPresets variant', () => {
  test('defaults to extended: presets render as chips', () => {
    const { container } = renderPresets()
    expect(chipNames(container)).toEqual(['Last 4 hours', 'Last 25 hours'])
  })

  test('condensed: renders no chips', () => {
    const { container } = renderPresets({ variant: 'condensed' })
    expect(chipNames(container)).toEqual([])
  })

  test('condensed: the dropdown offers every preset, including the Custom entry', async () => {
    const user = userEvent.setup()
    renderPresets({ variant: 'condensed', includeCustomEntry: true })
    await user.click(screen.getByRole('combobox', { name: 'Time ranges' }))
    await screen.findByRole('option', { name: 'Last 4 hours' })
    await screen.findByRole('option', { name: 'Last 25 hours' })
    await screen.findByRole('option', { name: 'Custom range' })
  })

  test('condensed: the trigger shows the active preset', () => {
    renderPresets({ variant: 'condensed', activePresetId: 'p2' })
    expect(screen.getByRole('combobox', { name: 'Time ranges' })).toHaveTextContent('Last 25 hours')
  })

  test('condensed: picking an option emits apply with that preset', async () => {
    const user = userEvent.setup()
    const { emitted } = renderPresets({ variant: 'condensed' })
    await user.click(screen.getByRole('combobox', { name: 'Time ranges' }))
    await user.click(await screen.findByRole('option', { name: 'Last 25 hours' }))
    expect(emitted).toEqual([PRESETS[1]])
  })
})
