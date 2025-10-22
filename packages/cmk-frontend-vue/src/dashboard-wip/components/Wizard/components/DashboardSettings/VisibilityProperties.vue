<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkHelpText from '@/components/CmkHelpText.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FieldComponent from '../TableForm/FieldComponent.vue'
import FieldDescription from '../TableForm/FieldDescription.vue'
import TableForm from '../TableForm/TableForm.vue'
import TableFormRow from '../TableForm/TableFormRow.vue'
import MonitorMenuTopicSelector from './MonitorMenuTopicSelector.vue'

const { _t } = usei18n()

const showInMonitorMenu = defineModel<boolean>('showInMonitorMenu', { required: true })
const monitorMenuTopic = defineModel<string>('monitorMenuTopic', { default: '' })
const sortIndex = defineModel<number>('sortIndex', { required: true })
</script>

<template>
  <div>
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Dashboard visibility') }}</FieldDescription>
        <FieldComponent>
          <MonitorMenuTopicSelector
            v-model:show-in-monitor-menu="showInMonitorMenu"
            v-model:selected-topic="monitorMenuTopic"
          />
          <div>
            <slot name="extra-visibility-settings" />
          </div>
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>
          {{ _t('Sort index') }}
          <CmkHelpText
            :help="
              _t(
                'You can set the order of the dashboard by changing this number. Lower numbers will be sorted first. Topics with the same number will be sorted alphabetically.'
              )
            "
          />
        </FieldDescription>
        <FieldComponent>
          <CmkInput :model-value="sortIndex" type="number" />
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </div>
</template>
