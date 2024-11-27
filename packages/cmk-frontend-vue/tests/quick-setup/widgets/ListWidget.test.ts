/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render, screen } from '@testing-library/vue'
import ListWidget from '@/quick-setup/components/quick-setup/widgets/ListWidget.vue'
import { getWidget } from '@/quick-setup/components/quick-setup/widgets/utils'
import { quickSetupGetWidgetKey } from '@/quick-setup/components/quick-setup/utils'

describe('ListWidget', () => {
  it('renders items', async () => {
    render(ListWidget, {
      global: {
        provide: {
          [quickSetupGetWidgetKey]: getWidget
        }
      },
      props: {
        list_type: 'bullet',
        items: [{ widget_type: 'text', text: 'Hello World' }]
      }
    })

    const items = screen.getAllByRole('listitem')
    expect(items.length).toBe(1)
    expect(screen.queryByText('Hello World')).toBeTruthy()
  })

  it('number style renders a <ol>', async () => {
    render(ListWidget, {
      global: {
        provide: {
          [quickSetupGetWidgetKey]: getWidget
        }
      },
      props: {
        list_type: 'ordered',
        items: [{ widget_type: 'text', text: 'Hello World' }]
      }
    })

    const list = screen.getByRole('list')
    expect(list.tagName).toBe('OL')
  })

  it('bullet style renders a <ul>', async () => {
    render(ListWidget, {
      global: {
        provide: {
          [quickSetupGetWidgetKey]: getWidget
        }
      },
      props: {
        list_type: 'bullet',
        items: [{ widget_type: 'text', text: 'Hello World' }]
      }
    })

    const list = screen.getByRole('list')
    expect(list.tagName).toBe('UL')
  })
})
