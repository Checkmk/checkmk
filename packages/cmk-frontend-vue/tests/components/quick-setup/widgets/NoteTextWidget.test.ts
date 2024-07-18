import { render, screen } from '@testing-library/vue'
import NoteTextWidget from '@/components/quick-setup/widgets/NoteTextWidget.vue'

test('NoteTextWidget renders value', async () => {
  render(NoteTextWidget, {
    props: {
      text: 'Hello World'
    }
  })

  expect(screen.queryByText('Hello World')).toBeTruthy()
})
