/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import CollapsibleWidget from '@/quick-setup/components/quick-setup/widgets/CollapsibleWidget.vue'
import { getWidget } from '@/quick-setup/components/quick-setup/widgets/utils'
import { quickSetupGetWidgetKey } from '@/quick-setup/components/quick-setup/utils'
import { fireEvent, render, screen } from '@testing-library/vue'

test('CollapsibleWidget renders values and label', async () => {
  render(CollapsibleWidget, {
    global: {
      provide: {
        [quickSetupGetWidgetKey]: getWidget
      }
    },
    props: {
      open: true,
      title: 'I am a label',
      help_text: 'I am a super helpful help text',
      items: [
        { widget_type: 'text', text: 'Welcome' },
        { widget_type: 'text', text: 'to Jurassic Park' }
      ]
    }
  })

  const trigger = screen.getByRole('button', { name: '?' })
  await fireEvent.click(trigger)
  await screen.findAllByText('I am a super helpful help text')
  screen.getByText('Welcome')
  screen.getByText('to Jurassic Park')
})
