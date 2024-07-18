import CollapsibleWidget from '@/components/quick-setup/widgets/CollapsibleWidget.vue'
import { render, screen } from '@testing-library/vue'

test('CollapsibleWidget renders values and label', async () => {
  render(CollapsibleWidget, {
    props: {
      open: true,
      label: 'I am a label',
      components: [
        { widget_type: 'text', text: 'Welcome' },
        { widget_type: 'text', text: 'to Jurassic Park' }
      ]
    }
  })

  expect(screen.queryByText('I am a label')).toBeTruthy()
  expect(screen.queryByText('Welcome')).toBeTruthy()
  expect(screen.queryByText('to Jurassic Park')).toBeTruthy()
})
