import CompositeWidget from '@/components/quick-setup/widgets/CompositeWidget.vue'
import { render, screen } from '@testing-library/vue'

test('CompositeWidget renders values and label', async () => {
  render(CompositeWidget, {
    props: {
      items: [
        { widget_type: 'text', text: 'Welcome' },
        { widget_type: 'text', text: 'to Jurassic Park' }
      ]
    }
  })

  expect(screen.queryByText('Welcome')).toBeTruthy()
  expect(screen.queryByText('to Jurassic Park')).toBeTruthy()
})
