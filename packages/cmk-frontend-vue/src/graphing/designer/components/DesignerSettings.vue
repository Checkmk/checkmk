<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkSlideInDialog from 'cmk-ui-library/components/CmkSlideInDialog.vue'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'

import { type CustomGraphOptions } from '../api'
import { type DataFieldErrors, useCustomGraphOptions } from '../composables/useCustomGraphOptions'
import GraphOptionRows from './GraphOptionRows.vue'

const { _t } = usei18n()

interface DesignerSettingsProps {
  graphOptions: CustomGraphOptions
}

interface DesignerSettingsEmits {
  updateSettings: [newGraphOptions: CustomGraphOptions]
}

const props = defineProps<DesignerSettingsProps>()
const emit = defineEmits<DesignerSettingsEmits>()
const open = defineModel<boolean>('open', { default: false })
const validationErrors = ref<DataFieldErrors>({})
const graphOptions = useCustomGraphOptions(() => props.graphOptions)

const closeSlideIn = () => {
  graphOptions.reset()
  validationErrors.value = {}
  open.value = false
}

const handleUpdate = () => {
  validationErrors.value = {}

  const result = graphOptions.validate()

  if (!result.isValid) {
    validationErrors.value = result.errors
    return
  }

  emit('updateSettings', result.graphOptions)
}
</script>

<template>
  <CmkSlideInDialog
    :open="open"
    size="small"
    :header="{ title: _t('Custom graph settings'), closeButton: true }"
    @close="closeSlideIn"
  >
    <div class="graphing-designer-settings__area">
      <div class="graphing-designer-settings__action-bar">
        <CmkButton variant="primary" @click="handleUpdate">{{ _t('Accept') }}</CmkButton>
        <CmkButton variant="optional" @click="closeSlideIn"
          ><CmkIcon name="cancel" size="small" /><CmkSpace size="small" />{{
            _t('Cancel')
          }}</CmkButton
        >
      </div>

      <div class="graphing-designer-settings__block">
        <CmkHeading type="h2">{{ _t('Graph options') }}</CmkHeading>
        <TableForm class="graphing-designer-settings__fields">
          <GraphOptionRows
            v-model:graph-options="graphOptions"
            :validation-errors="validationErrors"
          />
        </TableForm>
      </div>
    </div>
  </CmkSlideInDialog>
</template>

<style scoped>
.graphing-designer-settings__action-bar {
  display: flex;
  justify-content: flex-start;
  gap: var(--dimension-4);
}

.graphing-designer-settings__area {
  padding-bottom: var(--dimension-8);
}

.graphing-designer-settings__block {
  padding-top: var(--dimension-10);
}

.graphing-designer-settings__fields {
  padding-top: var(--dimension-6);
}
</style>
