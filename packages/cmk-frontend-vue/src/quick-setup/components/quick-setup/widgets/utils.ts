/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import TextWidget from './TextWidget.vue'
import NoteTextWidget from './NoteTextWidget.vue'
import DialogWidget from './DialogWidget.vue'
import ListWidget from './ListWidget.vue'
import NoneWidget from './NoneWidget.vue'
import FormSpecWidget from './FormSpecWidget.vue'
import CollapsibleWidget from './CollapsibleWidget.vue'
import FormSpecRecapWidget from './FormSpecRecapWidget.vue'
import type { ComponentSpec, FormSpecWidgetProps } from './widget_types'
import ConditionalNotificationECAlertStageWidget from '@/quick-setup/components/quick-setup/widgets/ConditionalNotificationECAlertStageWidget.vue'
import ConditionalNotificationServiceEventStageWidget from '@/quick-setup/components/quick-setup/widgets/ConditionalNotificationServiceEventStageWidget.vue'
import ConditionalNotificationDialogWidget from '@/quick-setup/components/quick-setup/widgets/ConditionalNotificationDialogWidget.vue'

export const getWidget = (widgetType: string): unknown => {
  //<component :is="getWidget(widgetType)" v-bind="widget_props" @update="update_data" />
  const map: Record<string, unknown> = {
    text: TextWidget,
    note_text: NoteTextWidget,
    dialog: DialogWidget,
    list_of_widgets: ListWidget,
    form_spec: FormSpecWidget,
    collapsible: CollapsibleWidget,
    form_spec_recap: FormSpecRecapWidget,
    conditional_notification_service_event_stage_widget:
      ConditionalNotificationServiceEventStageWidget,
    conditional_notification_ec_alert_stage_widget: ConditionalNotificationECAlertStageWidget,
    conditional_notification_dialog_widget: ConditionalNotificationDialogWidget
  }

  return widgetType in map ? map[widgetType] : NoneWidget
}

export const getFormSpecWidgets = (components: ComponentSpec[]): FormSpecWidgetProps[] => {
  const result: FormSpecWidgetProps[] = []

  for (const component of components) {
    if (component.widget_type === 'form_spec') {
      result.push(component as FormSpecWidgetProps)
    } else if (
      component.widget_type === 'collapsible' ||
      component.widget_type === 'conditional_notification_host_event_stage_widget' ||
      component.widget_type === 'conditional_notification_service_event_stage_widget' ||
      component.widget_type === 'conditional_notification_ec_alert_stage_widget' ||
      component.widget_type === 'conditional_notification_dialog_widget'
    ) {
      result.push(...getFormSpecWidgets(component.items))
    }
  }
  return result
}
