import TextWidget from '@/quick-setup/widgets/TextWidget.vue'
import NoteTextWidget from '@/quick-setup/widgets/NoteTextWidget.vue'
import ListWidget from '@/quick-setup/widgets/ListWidget.vue'
import NoneWidget from '@/quick-setup/widgets/NoneWidget.vue'
import FormSpecWidget from '@/quick-setup/widgets/FormSpecWidget.vue'
import CollapsibleWidget from '@/quick-setup/widgets/CollapsibleWidget.vue'
import FormSpecRecapWidget from '@/quick-setup/widgets/FormSpecRecapWidget.vue'
import type { ComponentSpec, FormSpecWidgetProps } from './widget_types'

export const getWidget = (widgetType: string): unknown => {
  //<component :is="getWidget(widgetType)" v-bind="widget_props" @update="update_data" />
  const map: Record<string, unknown> = {
    text: TextWidget,
    note_text: NoteTextWidget,
    list_of_widgets: ListWidget,
    form_spec: FormSpecWidget,
    collapsible: CollapsibleWidget,
    form_spec_recap: FormSpecRecapWidget
  }

  return widgetType in map ? map[widgetType] : NoneWidget
}

export const getFormSpecWidgets = (components: ComponentSpec[]): FormSpecWidgetProps[] => {
  const result: FormSpecWidgetProps[] = []

  for (const component of components) {
    if (component.widget_type === 'form_spec') {
      result.push(component as FormSpecWidgetProps)
    } else if (component.widget_type === 'collapsible') {
      result.push(...getFormSpecWidgets(component.items))
    }
  }
  return result
}
