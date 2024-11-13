/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/vue'
import HelpText from '@/components/HelpText.vue'

describe('HelpText', () => {
  test('renders help tooltip when click on trigger', async () => {
    render(HelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByTestId('help-icon')
    await fireEvent.click(trigger)
    const helpText = await screen.findAllByText('fooHelp')
    expect(helpText).toBeTruthy()
  })

  test('keep tooltip open when click on tooltip', async () => {
    render(HelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByTestId('help-icon')
    await fireEvent.click(trigger)
    const helpTooltip = await screen.findByRole('tooltip')
    await fireEvent.click(helpTooltip)
    await screen.findByRole('tooltip')
  })

  test('close tooltip when pressing escape key', async () => {
    render(HelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByTestId('help-icon')
    await fireEvent.click(trigger)
    await screen.findByRole('tooltip')

    await fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })
    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })
  })
})
