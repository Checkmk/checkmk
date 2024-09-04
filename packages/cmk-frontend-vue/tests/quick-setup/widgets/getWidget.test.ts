import { getWidget } from '@/quick-setup/widgets/utils'
import TextWidget from '@/quick-setup/widgets/TextWidget.vue'
import NoteTextWidget from '@/quick-setup/widgets/NoteTextWidget.vue'
import ListWidget from '@/quick-setup/widgets/ListWidget.vue'
import NoneWidget from '@/quick-setup/widgets/NoneWidget.vue'
import FormSpecWidget from '@/quick-setup/widgets/FormSpecWidget.vue'
import CollapsibleWidget from '@/quick-setup/widgets/CollapsibleWidget.vue'
import FormSpecRecapWidget from '@/quick-setup/widgets/FormSpecRecapWidget.vue'

test('getWidget returns NoneWidget when widget_type is unknown', async () => {
  expect(getWidget('i_do_not_exist')).toBe(NoneWidget)
  expect(getWidget('me_neither')).toBe(NoneWidget)
})

test('getWidget returns the proper widget', async () => {
  expect(getWidget('text')).toBe(TextWidget)
  expect(getWidget('note_text')).toBe(NoteTextWidget)
  expect(getWidget('list_of_widgets')).toBe(ListWidget)
  expect(getWidget('form_spec')).toBe(FormSpecWidget)
  expect(getWidget('collapsible')).toBe(CollapsibleWidget)
  expect(getWidget('form_spec_recap')).toBe(FormSpecRecapWidget)
})
