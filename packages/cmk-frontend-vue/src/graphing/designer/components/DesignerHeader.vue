<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { CustomGraphDesignerMode } from 'cmk-shared-typing/typescript/custom_graph_designer'
import type { GlobalTimePickerProps } from 'cmk-shared-typing/typescript/global_time_picker'
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkIcon from 'cmk-ui-library/components/CmkIcon'
import type { DateTimeRange } from 'cmk-ui-library/components/date-time'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { computed } from 'vue'

import { GlobalTimePicker, rollingRange, useGlobalTimeRange } from '../../GlobalTimePicker'
import GraphSelector, { type SelectableGraph } from './GraphSelector.vue'

const { selected, loggedInUser, mode, isEditable, timePicker } = defineProps<{
  selected: SelectableGraph | null
  loggedInUser: string
  mode: CustomGraphDesignerMode
  isEditable: boolean
  timePicker: GlobalTimePickerProps
}>()

const emit = defineEmits<{
  'enter-edit': []
  save: []
  'cancel-edit': []
  'graph-change': [graph: SelectableGraph]
  'enter-settings': []
}>()

const { _t } = usei18n()

// Drive the inner picker off the shared time-range singleton; the app seeds it before we mount.
const { activeTimeRange, setActiveTimeRange } = useGlobalTimeRange()
const range = computed<DateTimeRange>({
  get: () => activeTimeRange.value ?? rollingRange(timePicker.default_time_range),
  set: setActiveTimeRange
})
</script>

<template>
  <div class="graphing-designer-header">
    <div class="graphing-designer-header__selector">
      <CmkHeading>{{ _t('Custom graph') }}</CmkHeading>
      <GraphSelector
        :selected="selected"
        :logged-in-user="loggedInUser"
        :disabled="mode === 'edit'"
        @graph-change="emit('graph-change', $event)"
      />
    </div>
    <GlobalTimePicker
      v-model="range"
      class="graphing-designer-header__time-picker"
      :custom-time-ranges="timePicker.custom_time_ranges"
      :server-time-zone="timePicker.server_time_zone"
      :first-day-of-week="timePicker.first_day_of_week"
    />
    <div class="graphing-designer-header__actions">
      <template v-if="mode === 'view'">
        <CmkButton v-if="isEditable" variant="primary" @click="emit('enter-edit')">
          {{ _t('Edit custom graph') }}
        </CmkButton>
      </template>
      <template v-else>
        <CmkButton variant="optional" @click="emit('enter-settings')">
          <CmkIcon name="global-settings" variant="inline" size="small" />
          {{ _t('Settings') }}
        </CmkButton>
        <div class="graphing-designer-header__separator" />
        <CmkButton variant="primary" @click="emit('save')">
          {{ _t('Save') }}
        </CmkButton>
        <CmkButton variant="secondary" @click="emit('cancel-edit')">
          <CmkIcon name="cancel" variant="inline" size="small" />
          {{ _t('Cancel') }}
        </CmkButton>
      </template>
    </div>
  </div>
</template>

<style scoped>
.graphing-designer-header {
  display: flex;
  align-items: flex-end;
  gap: var(--dimension-6);
}

.graphing-designer-header__selector {
  display: flex;
  flex-direction: column;
  gap: var(--dimension-4);
}

/* Lift the compact controls onto the time picker's baseline (its trigger has bottom padding);
   this margin also provides the app header's bottom spacing. */
.graphing-designer-header__selector,
.graphing-designer-header__actions {
  margin-bottom: var(--dimension-7);
}

.graphing-designer-header__time-picker {
  flex: 1 1 auto;
  min-width: 0;
}

.graphing-designer-header__actions {
  display: flex;
  align-items: center;
  gap: var(--dimension-4);
}

.graphing-designer-header__separator {
  align-self: stretch;
  width: var(--dimension-1);
  padding: 0 var(--dimension-4);
  background-color: var(--button-optional-border-color);
  background-clip: content-box;
}
</style>
