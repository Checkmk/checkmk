import { getWidget } from "@/components/quick-setup/widgets/utils";
import TextWidget from '@/components/quick-setup/widgets/TextWidget.vue'
import NoteTextWidget from '@/components/quick-setup/widgets/NoteTextWidget.vue'
import ListWidget from '@/components/quick-setup/widgets/ListWidget.vue'
import NoneWidget from '@/components/quick-setup/widgets/NoneWidget.vue'
import FormSpecWidget from '@/components/quick-setup/widgets/FormSpecWidget.vue'
import CollapsibleWidget from '@/components/quick-setup/widgets/CollapsibleWidget.vue'


test('getWidget returns NoneWidget when widget_type is unknown', async () => {
    expect(getWidget('i_do_not_exist')).toBe(NoneWidget);
    expect(getWidget('me_neither')).toBe(NoneWidget);
});

test('getWidget returns the proper widget', async () => {
    expect(getWidget('text')).toBe(TextWidget);
    expect(getWidget('note_text')).toBe(NoteTextWidget);
    expect(getWidget('list_of_widgets')).toBe(ListWidget);
    expect(getWidget('form_spec')).toBe(FormSpecWidget);
    expect(getWidget('collapsible')).toBe(CollapsibleWidget);
});