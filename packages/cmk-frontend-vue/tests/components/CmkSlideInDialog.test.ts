/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkSlideInDialog from '@/components/CmkSlideInDialog.vue'

const helpTextComp = `<CmkHelpText :help="'some help'" />`

// We need to test the slideout specifically with and without a nested tooltip
// because the nested portals (dialog & tooltip) from radix break their auto
// focus functionality.
const createCmkSlideInDialogComp = (addHelp: boolean) =>
  defineComponent({
    components: { CmkSlideInDialog, CmkHelpText },
    setup() {
      const open = ref(false)
      return { open }
    },
    template: `
    <button @click="open = true">Open</button>
    <CmkSlideInDialog
      :open="open"
      :header="{ title: 'Some Title', closeButton: true }"
      @close="open = false"
      >
      <input data-testid="focus-element" />
      <div id="main">Main Content${addHelp ? helpTextComp : ``}</div>
    </CmkSlideInDialog>
`
  })

test.each([{ addTooltip: true }, { addTooltip: false }])(
  'Slidein shows and hides content',
  async ({ addTooltip }) => {
    render(createCmkSlideInDialogComp(addTooltip))

    expect(screen.queryByText('Main Content')).not.toBeInTheDocument()

    const button = screen.getByRole('button', { name: 'Open' })
    await fireEvent.click(button)

    await screen.findByText('Main Content')

    const closeButton = screen.getByRole('button', { name: 'Close' })
    await fireEvent.click(closeButton)

    await waitFor(() => expect(screen.queryByText('Main Content')).not.toBeInTheDocument())
  }
)

test.each([{ addTooltip: true }, { addTooltip: false }])(
  'Slidein auto focuses',
  async ({ addTooltip }) => {
    render(createCmkSlideInDialogComp(addTooltip))

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
    render(createCmkSlideInDialogComp(addTooltip))

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

test('Multiple slide-ins opened sequentially: body styles are managed correctly [CMK-28534]', async () => {
  render(
    defineComponent({
      components: { CmkSlideInDialog },
      setup() {
        const openFirst = ref(false)
        const openSecond = ref(false)
        return { openFirst, openSecond }
      },
      template: `
        <div>
          <button @click="openFirst = true">Open First</button>
          <CmkSlideInDialog
            :open="openFirst"
            :header="{ title: 'First Slide-in', closeButton: true }"
            @close="openFirst = false"
          >
            <div data-testid="first-content">First Content</div>
            <button @click="openSecond = true; openFirst = false">Open Second</button>
          </CmkSlideInDialog>
          <CmkSlideInDialog
            :open="openSecond"
            :header="{ title: 'Second Slide-in', closeButton: true }"
            @close="openSecond = false; openFirst = true"
          >
            <div data-testid="second-content">Second Content</div>
          </CmkSlideInDialog>
        </div>
      `
    })
  )

  expect(document.body.style.pointerEvents).toBe('')
  expect(document.body.style.overflow).toBe('')

  const firstButton = screen.getByRole('button', { name: 'Open First' })
  await fireEvent.click(firstButton)
  await screen.findByTestId('first-content')
  expect(screen.getByTestId('first-content')).toBeInTheDocument()

  expect(document.body.style.pointerEvents).toBe('none')

  const secondButton = screen.getByRole('button', { name: 'Open Second' })
  await fireEvent.click(secondButton)
  await screen.findByTestId('second-content')
  expect(screen.getByTestId('second-content')).toBeInTheDocument()

  const closeButton = screen.getByRole('button', { name: 'Close' })
  await fireEvent.click(closeButton)
  await waitFor(() => expect(screen.queryByTestId('second-content')).not.toBeInTheDocument())

  await screen.findByTestId('first-content')
  expect(screen.getByTestId('first-content')).toBeInTheDocument()

  expect(document.body.style.pointerEvents).toBe('none')

  const remainingCloseButton = screen.getByRole('button', { name: 'Close' })
  await fireEvent.click(remainingCloseButton)
  await waitFor(() => expect(screen.queryByTestId('first-content')).not.toBeInTheDocument())

  expect(document.body.style.pointerEvents).toBe('')
  expect(document.body.style.overflow).toBe('')
})
