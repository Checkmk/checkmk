import CollapsibleWidget from '@/quick-setup/widgets/CollapsibleWidget.vue'
import { render, screen } from '@testing-library/vue'

test('CollapsibleWidget renders values and label', async () => {
  render(CollapsibleWidget, {
    props: {
      open: true,
      title: 'I am a label',
      items: [
        { widget_type: 'text', text: 'Welcome' },
        { widget_type: 'text', text: 'to Jurassic Park' }
      ]
    }
  })

  expect(screen.queryByText('I am a label')).toBeTruthy()
  expect(screen.queryByText('Welcome')).toBeTruthy()
  expect(screen.queryByText('to Jurassic Park')).toBeTruthy()
})
