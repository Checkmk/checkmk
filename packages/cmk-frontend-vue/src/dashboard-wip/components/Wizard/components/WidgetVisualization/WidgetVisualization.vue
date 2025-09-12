<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FieldComponent from '../TableForm/FieldComponent.vue'
import FieldDescription from '../TableForm/FieldDescription.vue'
import TableForm from '../TableForm/TableForm.vue'
import TableFormRow from '../TableForm/TableFormRow.vue'

const { _t } = usei18n()

const title = defineModel<string>('title', { required: true })
const titleUrlEnabled = defineModel<boolean>('titleUrlEnabled', { required: true })
const titleUrl = defineModel<string>('titleUrl', { required: true })
const titleUrlValidationErrors = defineModel<string[]>('titleUrlValidationErrors', {
  required: true
})
const showTitle = defineModel<boolean>('showTitle', { required: true })
const showTitleBackground = defineModel<boolean>('showTitleBackground', { required: true })
const showWidgetBackground = defineModel<boolean>('showWidgetBackground', { required: true })
</script>

<template>
  <TableForm>
    <TableFormRow>
      <FieldDescription>{{ _t('Title') }}</FieldDescription>
      <FieldComponent>
        <div class="field-component__item">
          <CmkInput
            :model-value="title"
            type="text"
            field-size="MEDIUM"
            @update:model-value="(value) => (title = value || title)"
          />
        </div>

        <div class="field-component__item">
          <CmkCheckbox v-model="titleUrlEnabled" :label="_t('Link title to')" />
          <CmkIndent v-if="titleUrlEnabled">
            <CmkInput
              :model-value="titleUrl"
              type="text"
              field-size="MEDIUM"
              :external-errors="titleUrlValidationErrors"
              @update:model-value="(value) => (titleUrl = value || titleUrl)"
            />
          </CmkIndent>
        </div>
      </FieldComponent>
    </TableFormRow>

    <TableFormRow>
      <FieldDescription>{{ _t('Appearance') }}</FieldDescription>
      <FieldComponent>
        <div class="field-component__item">
          <CmkCheckbox v-model="showTitle" :label="_t('Show title')" />
        </div>
        <div class="field-component__item">
          <CmkCheckbox v-model="showTitleBackground" :label="_t('Show title background')" />
        </div>
        <div class="field-component__item">
          <CmkCheckbox v-model="showWidgetBackground" :label="_t('Show widget background')" />
        </div>
      </FieldComponent>
    </TableFormRow>
  </TableForm>
</template>
