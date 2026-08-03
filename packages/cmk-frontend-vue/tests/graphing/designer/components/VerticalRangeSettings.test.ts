/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { defineComponent, h, ref } from 'vue'

import VerticalRangeSettings from '@/graphing/designer/components/VerticalRangeSettings.vue'

function t(value: string): TranslatedString {
  return value as TranslatedString
}

interface Initial {
  verticalRangeType: string
  lowerBound: number | null
  upperBound: number | null
  lowerBoundError: TranslatedString | null
  upperBoundError: TranslatedString | null
}

const DEFAULTS: Initial = {
  verticalRangeType: 'auto',
  lowerBound: 0,
  upperBound: 1,
  lowerBoundError: null,
  upperBoundError: null
}

function renderVerticalRangeSettings(initial: Partial<Initial> = {}) {
  const state = { ...DEFAULTS, ...initial }
  const verticalRangeType = ref(state.verticalRangeType)
  const lowerBound = ref(state.lowerBound)
  const upperBound = ref(state.upperBound)

  const wrapper = defineComponent({
    setup() {
      return () =>
        h(VerticalRangeSettings, {
          verticalRangeType: verticalRangeType.value,
          'onUpdate:verticalRangeType': (v: string) => (verticalRangeType.value = v),
          lowerBound: lowerBound.value,
          'onUpdate:lowerBound': (v: number | null | undefined) => (lowerBound.value = v ?? null),
          upperBound: upperBound.value,
          'onUpdate:upperBound': (v: number | null | undefined) => (upperBound.value = v ?? null),
          lowerBoundError: state.lowerBoundError,
          upperBoundError: state.upperBoundError
        })
    }
  })

  render(wrapper)
  return { verticalRangeType, lowerBound, upperBound }
}

async function selectOption(comboboxName: string, optionName: string): Promise<void> {
  await fireEvent.click(screen.getByRole('combobox', { name: comboboxName }))
  await fireEvent.click(await screen.findByRole('option', { name: optionName }))
}

test('the bound fields are hidden when the range type is auto', () => {
  renderVerticalRangeSettings()

  expect(screen.getByRole('combobox', { name: 'Explicit range' })).toBeInTheDocument()
  expect(screen.queryByRole('spinbutton', { name: 'Lower limit' })).not.toBeInTheDocument()
  expect(screen.queryByRole('spinbutton', { name: 'Upper limit' })).not.toBeInTheDocument()
})

test('the bound fields are shown when the range type is fixed', () => {
  renderVerticalRangeSettings({ verticalRangeType: 'fixed', lowerBound: -5, upperBound: 10 })

  const lower = screen.getByRole('spinbutton', { name: 'Lower limit' })
  const upper = screen.getByRole('spinbutton', { name: 'Upper limit' })
  expect(lower).toHaveValue(-5)
  expect(upper).toHaveValue(10)
})

test('selecting Explicit range updates the model and reveals the bound fields', async () => {
  const { verticalRangeType } = renderVerticalRangeSettings()

  await selectOption('Explicit range', 'Explicit range')

  expect(verticalRangeType.value).toBe('fixed')
  expect(screen.getByRole('spinbutton', { name: 'Lower limit' })).toBeInTheDocument()
  expect(screen.getByRole('spinbutton', { name: 'Upper limit' })).toBeInTheDocument()
})

test('switching back to Auto hides the bound fields', async () => {
  renderVerticalRangeSettings({ verticalRangeType: 'fixed', lowerBound: -5, upperBound: 10 })

  await selectOption('Explicit range', 'Auto')

  expect(screen.queryByRole('spinbutton', { name: 'Lower limit' })).not.toBeInTheDocument()
  expect(screen.queryByRole('spinbutton', { name: 'Upper limit' })).not.toBeInTheDocument()
})

test('editing the lower bound updates the model', async () => {
  const { lowerBound } = renderVerticalRangeSettings({ verticalRangeType: 'fixed' })

  await fireEvent.update(screen.getByRole('spinbutton', { name: 'Lower limit' }), '-20')

  expect(lowerBound.value).toBe(-20)
})

test('editing the upper bound updates the model', async () => {
  const { upperBound } = renderVerticalRangeSettings({ verticalRangeType: 'fixed' })

  await fireEvent.update(screen.getByRole('spinbutton', { name: 'Upper limit' }), '20')

  expect(upperBound.value).toBe(20)
})

describe('validation errors', () => {
  test('shows no alert when there are no errors', () => {
    renderVerticalRangeSettings({ verticalRangeType: 'fixed' })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  test('shows the lower bound error message', () => {
    renderVerticalRangeSettings({
      verticalRangeType: 'fixed',
      lowerBoundError: t('Must specify the lower limit of the vertical range')
    })

    expect(
      screen.getByText('Must specify the lower limit of the vertical range')
    ).toBeInTheDocument()
  })

  test('shows the upper bound error message', () => {
    renderVerticalRangeSettings({
      verticalRangeType: 'fixed',
      upperBoundError: t('Must specify the upper limit of the vertical range')
    })

    expect(
      screen.getByText('Must specify the upper limit of the vertical range')
    ).toBeInTheDocument()
  })

  test('shows both error messages at once', () => {
    renderVerticalRangeSettings({
      verticalRangeType: 'fixed',
      lowerBoundError: t('Lower error'),
      upperBoundError: t('Upper error')
    })

    expect(screen.getByText('Lower error')).toBeInTheDocument()
    expect(screen.getByText('Upper error')).toBeInTheDocument()
  })
})
