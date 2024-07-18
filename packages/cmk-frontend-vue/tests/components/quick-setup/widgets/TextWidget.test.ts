import { render, screen } from '@testing-library/vue'
import TextWidget from '@/components/quick-setup/widgets/TextWidget.vue'

test('TextWidget renders value', async () => {
  render(TextWidget, {
    props: {
      text: 'Hello World'
    }
  })

  expect(screen.queryByText('Hello World')).toBeTruthy()
})
