import { render, screen } from '@testing-library/vue'
import ListWidget from '@/components/quick-setup/widgets/ListWidget.vue'

describe('ListWidget', () => {
  it('renders items', async () => {
    render(ListWidget, {
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
      props: {
        list_type: 'bullet',
        items: [{ widget_type: 'text', text: 'Hello World' }]
      }
    })

    const list = screen.getByRole('list')
    expect(list.tagName).toBe('UL')
  })
})
