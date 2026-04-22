/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import UclPropertiesPanel from '@ucl/_ucl/components/detail-page/UclPropertiesPanel.vue'
import type { PanelConfig } from '@ucl/_ucl/types/prop-panel'

import { copyToClipboard } from '@/lib/utils'

vi.mock('@/lib/utils', () => ({ copyToClipboard: vi.fn() }))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    resolve: ({ query }: { query: Record<string, string> }) => {
      const qs = new URLSearchParams(query).toString()
      return { href: qs ? `/?${qs}` : '/' }
    }
  }),
  useRoute: () => ({ query: {} })
}))

test('renders Properties heading', () => {
  render(UclPropertiesPanel, { props: { config: {}, modelValue: {} } })
  screen.getByText('Properties')
})

test('renders label for a boolean prop', () => {
  const config: PanelConfig = {
    enabled: { type: 'boolean', title: 'Enabled', initialState: false }
  }
  render(UclPropertiesPanel, { props: { config, modelValue: { enabled: false } } })
  screen.getByText('Enabled')
})

test('renders text input for a string prop', () => {
  const config: PanelConfig = {
    label: { type: 'string', title: 'Label', initialState: 'default' }
  }
  render(UclPropertiesPanel, { props: { config, modelValue: { label: 'default' } } })
  screen.getByRole('textbox')
})

test('renders number input for a number prop', () => {
  const config: PanelConfig = {
    count: { type: 'number', title: 'Count', initialState: 3 }
  }
  render(UclPropertiesPanel, { props: { config, modelValue: { count: 3 } } })
  expect(screen.getByRole('spinbutton')).toHaveValue(3)
})

test('renders textarea for a multiline-string prop', () => {
  const config: PanelConfig = {
    description: { type: 'multiline-string', title: 'Description', initialState: '' }
  }
  render(UclPropertiesPanel, { props: { config, modelValue: { description: '' } } })
  expect(screen.getByRole('textbox').tagName).toBe('TEXTAREA')
})

test('renders labels for all props in config', () => {
  const config: PanelConfig = {
    enabled: { type: 'boolean', title: 'Enabled', initialState: true },
    label: { type: 'string', title: 'Label text', initialState: '' }
  }
  render(UclPropertiesPanel, { props: { config, modelValue: { enabled: true, label: '' } } })

  screen.getByText('Enabled')
  screen.getByText('Label text')
})

test('copy button writes encoded non-default property values to clipboard URL', async () => {
  const config: PanelConfig = {
    enabled: { type: 'boolean', title: 'Enabled', initialState: false },
    label: { type: 'string', title: 'Label', initialState: 'default' },
    count: { type: 'number', title: 'Count', initialState: 0 }
  }

  render(UclPropertiesPanel, {
    props: {
      config,
      modelValue: { enabled: true, label: 'custom label', count: 42 }
    }
  })

  await userEvent.click(screen.getByRole('button', { name: 'Copy permalink' }))

  const url = new URL(vi.mocked(copyToClipboard).mock.lastCall![0])
  expect(url.searchParams.get('enabled')).toBe('1')
  expect(url.searchParams.get('label')).toBe('custom label')
  expect(url.searchParams.get('count')).toBe('42')
})

test('default property values are absent from the copied URL', async () => {
  const config: PanelConfig = {
    enabled: { type: 'boolean', title: 'Enabled', initialState: false },
    label: { type: 'string', title: 'Label', initialState: 'default' }
  }

  render(UclPropertiesPanel, {
    props: {
      config,
      modelValue: { enabled: false, label: 'default' }
    }
  })

  await userEvent.click(screen.getByRole('button', { name: 'Copy permalink' }))

  const url = new URL(vi.mocked(copyToClipboard).mock.lastCall![0])
  expect(url.search).toBe('')
})
