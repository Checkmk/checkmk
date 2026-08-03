/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'
import { defineComponent, h, ref } from 'vue'

import type { CustomGraphUnitNotationTypes } from '@/graphing/designer/api'
import UnitSettings from '@/graphing/designer/components/UnitSettings.vue'

function t(value: string): TranslatedString {
  return value as TranslatedString
}

interface Initial {
  unitType: 'first_entry_with_unit' | 'custom'
  notation: CustomGraphUnitNotationTypes | 'time' | null
  symbol: string
  roundingMode: 'auto' | 'strict' | null
  roundingDigits: number | undefined
  digitError: TranslatedString | null
}

const DEFAULTS: Initial = {
  unitType: 'first_entry_with_unit',
  notation: null,
  symbol: '',
  roundingMode: null,
  roundingDigits: 2,
  digitError: null
}

function renderUnitSettings(initial: Partial<Initial> = {}) {
  const state = { ...DEFAULTS, ...initial }
  const unitType = ref(state.unitType)
  const notation = ref(state.notation)
  const symbol = ref(state.symbol)
  const roundingMode = ref(state.roundingMode)
  const roundingDigits = ref(state.roundingDigits)

  const wrapper = defineComponent({
    setup() {
      return () =>
        h(UnitSettings, {
          unitType: unitType.value,
          'onUpdate:unitType': (v: Initial['unitType']) => (unitType.value = v),
          notation: notation.value,
          'onUpdate:notation': (v: Initial['notation']) => (notation.value = v),
          symbol: symbol.value,
          'onUpdate:symbol': (v: string) => (symbol.value = v),
          roundingMode: roundingMode.value,
          'onUpdate:roundingMode': (v: Initial['roundingMode']) => (roundingMode.value = v),
          roundingDigits: roundingDigits.value,
          'onUpdate:roundingDigits': (v: number | undefined) => (roundingDigits.value = v),
          digitError: state.digitError
        })
    }
  })

  render(wrapper)
  return { unitType, notation, symbol, roundingMode, roundingDigits }
}

async function selectOption(comboboxName: string, optionName: string): Promise<void> {
  await fireEvent.click(screen.getByRole('combobox', { name: comboboxName }))
  await fireEvent.click(await screen.findByRole('option', { name: optionName }))
}

test('only the unit dropdown is shown when the unit type is first_entry_with_unit', () => {
  renderUnitSettings()

  expect(screen.getByRole('combobox', { name: 'Unit' })).toBeInTheDocument()
  expect(screen.queryByRole('combobox', { name: 'Notation' })).not.toBeInTheDocument()
  expect(screen.queryByRole('textbox', { name: 'Symbol' })).not.toBeInTheDocument()
  expect(screen.queryByRole('combobox', { name: 'Rounding mode' })).not.toBeInTheDocument()
  expect(screen.queryByRole('spinbutton', { name: 'Rounding digits' })).not.toBeInTheDocument()
})

test('selecting Custom updates the model and reveals the custom unit fields', async () => {
  const { unitType } = renderUnitSettings()

  await selectOption('Unit', 'Custom')

  expect(unitType.value).toBe('custom')
  expect(screen.getByRole('combobox', { name: 'Notation' })).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: 'Symbol' })).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Rounding mode' })).toBeInTheDocument()
  expect(screen.getByRole('spinbutton', { name: 'Rounding digits' })).toBeInTheDocument()
})

test('switching back to first_entry_with_unit hides the custom unit fields', async () => {
  renderUnitSettings({ unitType: 'custom', notation: 'decimal', symbol: 'MB' })

  await selectOption('Unit', 'Use unit of first entry')

  expect(screen.queryByRole('combobox', { name: 'Notation' })).not.toBeInTheDocument()
  expect(screen.queryByRole('textbox', { name: 'Symbol' })).not.toBeInTheDocument()
})

test('the symbol field is hidden for a time notation', () => {
  renderUnitSettings({ unitType: 'custom', notation: 'time' })

  expect(screen.getByRole('combobox', { name: 'Notation' })).toBeInTheDocument()
  expect(screen.queryByRole('textbox', { name: 'Symbol' })).not.toBeInTheDocument()
})

test('changing the notation to Time hides the symbol field and updates the model', async () => {
  const { notation } = renderUnitSettings({
    unitType: 'custom',
    notation: 'decimal',
    symbol: 'MB'
  })
  expect(screen.getByRole('textbox', { name: 'Symbol' })).toBeInTheDocument()

  await selectOption('Notation', 'Time')

  expect(notation.value).toBe('time')
  expect(screen.queryByRole('textbox', { name: 'Symbol' })).not.toBeInTheDocument()
})

test('editing the symbol updates the model', async () => {
  const { symbol } = renderUnitSettings({ unitType: 'custom', notation: 'decimal' })

  await fireEvent.update(screen.getByRole('textbox', { name: 'Symbol' }), 'GB')

  expect(symbol.value).toBe('GB')
})

test('selecting a rounding mode updates the model', async () => {
  const { roundingMode } = renderUnitSettings({ unitType: 'custom', notation: 'decimal' })

  await selectOption('Rounding mode', 'Strict')

  expect(roundingMode.value).toBe('strict')
})

test('editing the rounding digits updates the model', async () => {
  const { roundingDigits } = renderUnitSettings({ unitType: 'custom', notation: 'decimal' })

  await fireEvent.update(screen.getByRole('spinbutton', { name: 'Rounding digits' }), '5')

  expect(roundingDigits.value).toBe(5)
})

describe('digitError', () => {
  test('shows no alert when there is no error', () => {
    renderUnitSettings({ unitType: 'custom', notation: 'decimal' })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  test('shows the digit error message', () => {
    renderUnitSettings({
      unitType: 'custom',
      notation: 'decimal',
      digitError: t('The number of digits for rounding must be a non-negative integer')
    })

    expect(
      screen.getByText('The number of digits for rounding must be a non-negative integer')
    ).toBeInTheDocument()
  })
})
