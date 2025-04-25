/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import SlideIn from '@/components/SlideIn.vue'
import { fireEvent, render, screen, waitForElementToBeRemoved } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'
import userEvent from '@testing-library/user-event'
import HelpText from '@/components/HelpText.vue'

const helpTextComp = `<HelpText :help="'some help'" />`

// We need to test the slideout specifically with and without a nested tooltip
// because the nested portals (dialog & tooltip) from radix break their auto
// focus functionality.
const createSlideInComp = (addHelp: boolean) =>
  defineComponent({
    components: { SlideIn, HelpText },
    setup() {
      const open = ref(false)
      return { open }
    },
    template: `
    <button @click="open = true">Open</button>
    <SlideIn
      :open="open"
      :header="{ title: 'Some Title', closeButton: true }"
      @close="open = false"
      >
      <input data-testid="focus-element" />
      <div id="main">Main Content${addHelp ? helpTextComp : ``}</div>
    </SlideIn>
`
  })

test.each([{ addTooltip: true }, { addTooltip: false }])(
  'Slidein shows and hides content',
  async ({ addTooltip }) => {
    render(createSlideInComp(addTooltip))

    expect(screen.queryByText('Main Content')).not.toBeInTheDocument()

    const button = screen.getByRole('button', { name: 'Open' })
    await fireEvent.click(button)

    await screen.findByText('Main Content')

    const closeButton = screen.getByRole('button', { name: 'Close' })
    await fireEvent.click(closeButton)

    await waitForElementToBeRemoved(() => screen.queryByText('Main Content'))
  }
)

test.each([{ addTooltip: true }, { addTooltip: false }])(
  'Slidein auto focuses',
  async ({ addTooltip }) => {
    render(createSlideInComp(addTooltip))

    expect(document.activeElement).toBe(document.body)

    const button = screen.getByRole('button', { name: 'Open' })
    await fireEvent.click(button)

    const slideIn = await screen.findByRole('dialog')
    expect(document.activeElement).toBe(slideIn)
  }
)

test.each([{ addTooltip: true }, { addTooltip: false }])(
  'Slidein supports tabbing',
  async ({ addTooltip }) => {
    render(createSlideInComp(addTooltip))

    const button = screen.getByRole('button', { name: 'Open' })
    await fireEvent.click(button)

    // wait for the slideIn to be open
    await screen.findByText('Main Content')

    await userEvent.tab()
    const closeButton = screen.getByRole('button', { name: 'Close' })
    expect(document.activeElement).toBe(closeButton)

    await userEvent.tab()
    const autoFocusElement = screen.getByTestId('focus-element')
    expect(document.activeElement).toBe(autoFocusElement)
  }
)
