<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown.vue'
import CmkIndent from '@/components/CmkIndent.vue'
import HelpText from '@/components/HelpText.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FieldComponent from '../TableForm/FieldComponent.vue'
import FieldDescription from '../TableForm/FieldDescription.vue'
import TableForm from '../TableForm/TableForm.vue'
import TableFormRow from '../TableForm/TableFormRow.vue'

const { _t } = usei18n()

const showInMonitorMenu = defineModel<boolean>('showInMonitorMenu', { required: true })
const monitorMenu = defineModel<string>('monitorMenu', { default: '' })
const sortIndex = defineModel<number>('sortIndex', { required: true })
</script>

<template>
  <div>
    <TableForm>
      <TableFormRow>
        <FieldDescription>{{ _t('Dashboard visibility') }}</FieldDescription>
        <FieldComponent>
          <CmkCheckbox v-model="showInMonitorMenu" :label="_t('Show in monitor menu')" />
          <CmkIndent v-if="showInMonitorMenu">
            <CmkDropdown
              :selected-option="monitorMenu"
              :label="_t('Select option')"
              :options="{
                type: 'fixed',
                suggestions: [
                  { name: 'dashboards', title: _t('Dashboards') },
                  { name: 'TBD', title: _t('To be defined') }
                ]
              }"
              @update:selected-option="(value) => (monitorMenu = value || monitorMenu)"
            />
          </CmkIndent>
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>
          {{ _t('Sort index') }}
          <HelpText
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
