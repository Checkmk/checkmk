/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import userEvent from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'

import CmkHelpText from '@/components/CmkHelpText.vue'

describe('CmkHelpText', () => {
  test('renders help tooltip when click on trigger', async () => {
    const user = userEvent.setup()
    render(CmkHelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByRole('button')
    await user.click(trigger)
    const helpText = await screen.findAllByText('fooHelp')
    expect(helpText).toBeTruthy()
  })

  test('keep tooltip open when click on tooltip', async () => {
    const user = userEvent.setup()
    render(CmkHelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByRole('button')
    await user.click(trigger)
    const helpTooltip = await screen.findByRole('tooltip')
    await user.click(helpTooltip)
    await screen.findByRole('tooltip')
  })

  test('close open tooltip when clicking on icon', async () => {
    const user = userEvent.setup()
    render(CmkHelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByRole('button')
    await user.click(trigger)
    expect(screen.queryByRole('tooltip')).toBeInTheDocument()
    await user.click(trigger)
    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })
  })

  test('close tooltip when pressing escape key', async () => {
    const user = userEvent.setup()
    render(CmkHelpText, {
      props: {
        help: 'fooHelp'
      }
    })
    const trigger = await screen.findByRole('button')
    await user.click(trigger)
    await screen.findByRole('tooltip')

    await user.keyboard('[Escape]')
    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })
  })

  test('is keyboard focusable and toggles via Enter', async () => {
    const user = userEvent.setup()
    render(CmkHelpText, { props: { help: 'fooHelp' } })

    await user.tab()

    await user.keyboard('[Enter]')

    screen.getByRole('tooltip')

    await user.keyboard('[Enter]')

    await waitFor(() => {
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })
  })
})
