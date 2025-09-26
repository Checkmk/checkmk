<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed, useAttrs } from 'vue'

import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import CmkSpace from '@/components/CmkSpace.vue'
import HelpText from '@/components/HelpText.vue'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import { useDebounceFn } from '@/dashboard-wip/composables/useDebounce'

import IconSelector from '../IconSelector.vue'
import FieldComponent from '../TableForm/FieldComponent.vue'
import FieldDescription from '../TableForm/FieldDescription.vue'
import TableForm from '../TableForm/TableForm.vue'
import TableFormRow from '../TableForm/TableFormRow.vue'
import { generateUniqueId, isIdInUse, toSnakeCase } from './utils'

const { _t } = usei18n()

interface GeneralPropertiesProps {
  nameValidationErrors: string[]
  uniqueIdValidationErrors: string[]
  originalDashboardId?: string
}

const props = defineProps<GeneralPropertiesProps>()

const name = defineModel<string>('name', { required: true })
const addFilterSuffix = defineModel<boolean>('addFilterSuffix', { required: false })
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

const _generateUniqueId = async (base: string) => {
  uniqueId.value = (await isIdInUse(base, props?.originalDashboardId))
    ? await generateUniqueId(base, props?.originalDashboardId)
    : base
}
const _debouncedGenerateUniqueId = useDebounceFn(_generateUniqueId, 300)

const _updateDashboardName = (newName?: string) => {
  if (newName) {
    name.value = newName
    if (createUniqueId.value) {
      _debouncedGenerateUniqueId(toSnakeCase(newName.trim()))
    }
  }
}

const attrs = useAttrs()
const displaySuffixInput = computed(() => 'addFilterSuffix' in attrs)
</script>

<template>
  <div>
    <TableForm>
      <TableFormRow>
        <FieldDescription>
          {{ _t('Name') }}<CmkSpace /><span class="db-general-properties--required">{{
            _t('required')
          }}</span>
        </FieldDescription>
        <FieldComponent>
          <div class="db-general-properties__item">
            <CmkInput
              :model-value="name"
              :placeholder="_t('Enter name')"
              :aria-label="_t('Enter name')"
              type="text"
              :external-errors="nameValidationErrors"
              required
              @update:model-value="_updateDashboardName"
            />
          </div>
          <div v-if="displaySuffixInput" class="db-general-properties__item">
            <CmkCheckbox
              v-model="addFilterSuffix!"
              :label="_t('Add filter as suffix')"
              :help="_t('Include dashboard filter contents to the dashboard title.')"
            />
          </div>
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>
          {{ _t('Unique ID') }}<CmkSpace /><span class="db-general-properties--required">{{
            _t('required')
          }}</span>
        </FieldDescription>
        <FieldComponent>
          <div class="db-general-properties__item">
            <CmkCheckbox
              v-model="createUniqueId"
              :label="_t('Automatically create unique ID')"
            /><span v-if="createUniqueId">: {{ uniqueId }}</span>
          </div>
          <div v-if="!createUniqueId" class="db-general-properties__item">
            <CmkIndent>
              <CmkInput
                :model-value="uniqueId"
                :placeholder="_t('Add unique ID')"
                :aria-label="_t('Add unique ID')"
                type="text"
                required
                :external-errors="uniqueIdValidationErrors"
                @update:model-value="(val: string | undefined) => (uniqueId = val || uniqueId)"
              />
            </CmkIndent>
          </div>
        </FieldComponent>
      </TableFormRow>

      <TableFormRow>
        <FieldDescription>
          {{ _t('Dashboard icon') }}
          <HelpText
            :help="
              _t(
                'This selection is only relevant if under \'User\' -> \'Edit Profile\' -> \'Mega menue icons\' you have selected the options \'Per Entry\'. You can select the icon to display next to your dashboard in the Monitoring menu. You can choose either a single colored icon or one with an additional symbol.'
              )
            "
          />
        </FieldDescription>
        <FieldComponent>
          <div class="db-general-properties__item">
            <IconSelector :selected-icon="dashboardIcon" :selected-emblem="dashboardEmblem" />
          </div>
        </FieldComponent>
      </TableFormRow>
    </TableForm>
  </div>
</template>

<style scoped>
.db-general-properties--required {
  color: var(--form-element-required-color);
}

.db-general-properties--required::before {
  content: '(';
}

.db-general-properties--required::after {
  content: ')';
}

.db-general-properties__item {
  display: block;
  padding-bottom: var(--spacing-half);
}
</style>
