<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkInput from '@/components/user-input/CmkInput.vue'

import ContentSpacer from '../../../components/ContentSpacer.vue'
import GeneralProperties from '../../../components/DashboardSettings/GeneralProperties.vue'
import FieldComponent from '../../../components/TableForm/FieldComponent.vue'
import FieldDescription from '../../../components/TableForm/FieldDescription.vue'
import TableForm from '../../../components/TableForm/TableForm.vue'
import TableFormRow from '../../../components/TableForm/TableFormRow.vue'

const { _t } = usei18n()

interface GeneralSettingsProps {
  nameValidationErrors: string[]
  uniqueIdValidationErrors: string[]
  dashboardType: string
  originalDashboardId: string
}

defineProps<GeneralSettingsProps>()
const name = defineModel<string>('name', { required: true })
const description = defineModel<string | null>('description', { required: true })
const addFilterSuffix = defineModel<boolean>('addFilterSuffix', { required: true })
const createUniqueId = defineModel<boolean>('createUniqueId', { required: true })
const uniqueId = defineModel<string>('uniqueId', { required: true })
const dashboardIcon = defineModel<string | null>('dashboardIcon', {
  required: false,
  default: null
})
const dashboardEmblem = defineModel<string | null>('dashboardEmblem', {
  required: false,
  default: null
})
</script>

<template>
  <TableForm>
    <TableFormRow>
      <FieldDescription>{{ _t('Dashboard type') }}</FieldDescription>
      <FieldComponent>{{ dashboardType }}</FieldComponent>
    </TableFormRow>
  </TableForm>

  <ContentSpacer />

  <GeneralProperties
    v-model:name="name"
    v-model:create-unique-id="createUniqueId"
    v-model:unique-id="uniqueId"
    v-model:dashboard-icon="dashboardIcon"
    v-model:dashboard-emblem="dashboardEmblem"
    :name-validation-errors="[]"
    :add-filter-suffix="addFilterSuffix"
    :unique-id-validation-errors="[]"
    :original-dashboard-id="originalDashboardId"
    @update:add-filter-suffix="(value) => value || addFilterSuffix"
  />

  <ContentSpacer />

  <TableForm>
    <TableFormRow>
      <FieldDescription>{{ _t('Description') }}</FieldDescription>
      <FieldComponent>
        <CmkInput
          :placeholder="_t('Enter description')"
          :aria-label="_t('Enter description')"
          type="text"
          field-size="LARGE"
          :external-errors="nameValidationErrors"
          required
          @update:model-value="(name) => (description = name || '')"
        />
      </FieldComponent>
    </TableFormRow>
  </TableForm>
</template>
