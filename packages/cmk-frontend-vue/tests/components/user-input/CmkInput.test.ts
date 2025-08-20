/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { ref, defineComponent } from 'vue'
import { userEvent } from '@testing-library/user-event'
import CmkInput from '@/components/user-input/CmkInput.vue'
import { render, screen } from '@testing-library/vue'

test('CmkInput can be labelled on component', async () => {
  render(
    defineComponent({
      components: { CmkInput },
      setup() {
        const data = ref('foo')
        return { data }
      },
      template: `
        <CmkInput
          v-model:data="data"
          aria-label="some aria label"
        />
      `
    })
  )

  screen.getByRole('textbox', { name: 'some aria label' })
})

test('CmkInput can be labelled externally', async () => {
  render(
    defineComponent({
      components: { CmkInput },
      setup() {
        const data = ref('foo')
        return { data }
      },
      template: `
        <label for="input-id">some aria label</label>
        <CmkInput
          id="input-id"
          v-model:data="data"
        />
      `
    })
  )

  screen.getByRole('textbox', { name: 'some aria label' })
})

test('CmkInput switches aria-role on type', async () => {
  render(CmkInput, {
    props: {
      modelValue: 'foo',
      type: 'number'
    }
  })

  screen.getByRole('spinbutton')
})

test('CmkInput validates input', async () => {
  const data: string | number = ''
  render(CmkInput, {
    props: {
      modelValue: data,
      validators: [(v: unknown) => ((v as string) === 'bar' ? ['bar not allowed'] : [])]
    }
  })

  const input = screen.getByRole('textbox')

  await userEvent.type(input, 'bar')

  expect(await screen.findByText('bar not allowed')).toBeInTheDocument()
})

test('CmkInput renders updated validation', async () => {
  const props: typeof CmkInput.props = {
    modelValue: 'foo',
    externalErrors: ['some old validation']
  }

  const { rerender } = render(CmkInput, { props })

  props.externalErrors = ['some new validation']

  await rerender(props)

  await screen.findByText('some new validation')
})

test('CmkInput local validators override external errors', async () => {
  const data: string = ''
  render(CmkInput, {
    props: {
      modelValue: data,
      externalErrors: ['some validation'],
      validators: [(v: unknown) => ((v as string) === 'foo' ? ['foo not allowed'] : [])]
    }
  })

  const input = screen.getByRole('textbox')
  await userEvent.type(input, 'foo')

  await screen.findByText('foo not allowed')
  expect(screen.queryByText('some validation')).not.toBeInTheDocument()
})

test('CmkInput changes do not reset external validations without local validators', async () => {
  const data: string = ''
  render(CmkInput, {
    props: {
      modelValue: data,
      externalErrors: ['some validation']
    }
  })

  const input = screen.getByRole('textbox')
  await userEvent.type(input, 'foo')

  await screen.findByText('some validation')
})
