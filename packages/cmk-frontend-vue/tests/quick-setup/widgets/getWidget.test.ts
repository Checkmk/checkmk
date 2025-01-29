/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { getWidget } from '@/quick-setup/components/quick-setup/widgets/utils'
import TextWidget from '@/quick-setup/components/quick-setup/widgets/TextWidget.vue'
import NoteTextWidget from '@/quick-setup/components/quick-setup/widgets/NoteTextWidget.vue'
import ListWidget from '@/quick-setup/components/quick-setup/widgets/ListWidget.vue'
import NoneWidget from '@/quick-setup/components/quick-setup/widgets/NoneWidget.vue'
import FormSpecWidget from '@/quick-setup/components/quick-setup/widgets/FormSpecWidget.vue'
import CollapsibleWidget from '@/quick-setup/components/quick-setup/widgets/CollapsibleWidget.vue'
import FormSpecRecapWidget from '@/quick-setup/components/quick-setup/widgets/FormSpecRecapWidget.vue'
import ConditionalNotificationServiceEventStageWidget from '@/quick-setup/components/quick-setup/widgets/ConditionalNotificationServiceEventStageWidget.vue'
import ConditionalNotificationECAlertStageWidget from '@/quick-setup/components/quick-setup/widgets/ConditionalNotificationECAlertStageWidget.vue'

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
  expect(getWidget('conditional_notification_service_event_stage_widget')).toBe(
    ConditionalNotificationServiceEventStageWidget
  )
  expect(getWidget('conditional_notification_ec_alert_stage_widget')).toBe(
    ConditionalNotificationECAlertStageWidget
  )
})
