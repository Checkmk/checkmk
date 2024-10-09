/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { fireEvent, render, screen } from '@testing-library/vue'
import HelpText from '@/components/HelpText.vue'

describe('HelpText', () => {
  test('renders help tooltip when click on trigger', async () => {
    render(HelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByTestId('help-tooltip-trigger')
    expect(trigger).toBeTruthy()
    expect(trigger).toHaveClass('trigger')
    await fireEvent.click(trigger)
    const helpText = screen.findByText('fooHelp')
    expect(helpText).toBeTruthy()
  })

  test('keep tooltip open when click on tooltip', async () => {
    render(HelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByTestId('help-tooltip-trigger')
    await fireEvent.click(trigger)
    const helpTooltip = await screen.findByRole('tooltip')
    expect(helpTooltip).toBeTruthy()
    await fireEvent.click(helpTooltip)
    expect(helpTooltip).toBeTruthy()
  })

  test('close tooltip when pressing escape key', async () => {
    render(HelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByTestId('help-tooltip-trigger')
    await fireEvent.click(trigger)
    let helpTooltip = await screen.findByRole('tooltip')
    expect(helpTooltip).toBeTruthy()

    await fireEvent.keyDown(document, { key: 'Escape', code: 'Escape' })
    helpTooltip = await screen.findByRole('tooltip')
    expect(helpTooltip).not.toBeInTheDocument()
  })
})
