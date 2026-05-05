/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import UclPropertiesPanel from '@ucl/_ucl/components/detail-page/UclPropertiesPanel.vue'
import type { PanelConfig } from '@ucl/_ucl/types/prop-panel'
import { createPanelState } from '@ucl/_ucl/types/prop-panel'
import { type PropType, defineComponent, ref } from 'vue'

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

describe('prop type interactions update component', () => {
  const dummyConfig = {
    booleanProp: { type: 'boolean', title: 'Boolean', initialState: false },
    stringProp: { type: 'string', title: 'String', initialState: '' },
    numberProp: { type: 'number', title: 'Number', initialState: 0 },
    multilineStringProp: {
      type: 'multiline-string',
      title: 'Multiline string',
      initialState: ''
    },
    stringArrayProp: {
      type: 'string-array',
      title: 'String array',
      initialState: [] as string[]
    },
    listProp: {
      type: 'list',
      title: 'List',
      initialState: 'option-a',
      options: [
        { name: 'option-a', title: 'Option A' },
        { name: 'option-b', title: 'Option B' }
      ]
    }
  } satisfies PanelConfig

  function makeTestApp() {
    // eslint-disable-next-line @typescript-eslint/naming-convention
    const DummyComponent = defineComponent({
      props: {
        booleanProp: { type: Boolean, required: true },
        stringProp: { type: String, required: true },
        numberProp: { type: Number, required: true },
        multilineStringProp: { type: String, required: true },
        stringArrayProp: { type: Array as PropType<string[]>, required: true },
        listProp: { type: String, required: true }
      },
      template: `
        <div>
          <span data-testid="boolean-prop">{{ booleanProp }}</span>
          <span data-testid="string-prop">{{ stringProp }}</span>
          <span data-testid="number-prop">{{ numberProp }}</span>
          <pre data-testid="multiline-string-prop">{{ multilineStringProp }}</pre>
          <ul data-testid="string-array-prop">
            <li v-for="item in stringArrayProp" :key="item">{{ item }}</li>
          </ul>
          <span data-testid="list-prop">{{ listProp }}</span>
        </div>
      `
    })

    return defineComponent({
      components: { UclPropertiesPanel, DummyComponent },
      setup() {
        const propState = ref(createPanelState(dummyConfig))
        return { propState, config: dummyConfig }
      },
      template: `
        <UclPropertiesPanel :config="config" v-model="propState" />
        <DummyComponent
          :booleanProp="propState.booleanProp"
          :stringProp="propState.stringProp"
          :numberProp="propState.numberProp"
          :multilineStringProp="propState.multilineStringProp"
          :stringArrayProp="propState.stringArrayProp"
          :listProp="propState.listProp"
        />
      `
    })
  }

  test('boolean', async () => {
    render(makeTestApp())
    expect(screen.getByTestId('boolean-prop')).toHaveTextContent('false')
    await userEvent.click(screen.getByRole('checkbox'))
    expect(screen.getByTestId('boolean-prop')).toHaveTextContent('true')
  })

  test('string', async () => {
    render(makeTestApp())
    expect(screen.getByTestId('string-prop')).toBeEmptyDOMElement()
    await userEvent.type(screen.getByLabelText('String'), 'hello')
    expect(screen.getByTestId('string-prop')).toHaveTextContent('hello')
  })

  test('number', async () => {
    render(makeTestApp())
    expect(screen.getByTestId('number-prop')).toHaveTextContent('0')
    const spinbutton = screen.getByRole('spinbutton')
    await userEvent.clear(spinbutton)
    await userEvent.type(spinbutton, '42')
    expect(screen.getByTestId('number-prop')).toHaveTextContent('42')
  })

  test('multiline-string', async () => {
    render(makeTestApp())
    await userEvent.type(screen.getByLabelText('Multiline string'), 'first line{Enter}second line')
    expect(screen.getByTestId('multiline-string-prop').textContent).toBe('first line\nsecond line')
  })

  test('string-array', async () => {
    render(makeTestApp())
    expect(screen.queryAllByRole('listitem')).toHaveLength(0)
    await userEvent.type(screen.getByLabelText('String array'), 'alpha{Enter}beta{Enter}gamma')
    expect(screen.getAllByRole('listitem').map((li) => li.textContent)).toEqual([
      'alpha',
      'beta',
      'gamma'
    ])
  })

  test('list', async () => {
    render(makeTestApp())
    expect(screen.getByTestId('list-prop')).toHaveTextContent('option-a')
    await userEvent.click(screen.getByRole('combobox', { name: 'List' }))
    await userEvent.click(await screen.findByRole('option', { name: 'Option B' }))
    expect(screen.getByTestId('list-prop')).toHaveTextContent('option-b')
  })
})
