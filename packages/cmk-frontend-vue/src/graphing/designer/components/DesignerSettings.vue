<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton/CmkButton.vue'
import CmkIcon from 'cmk-ui-library/components/CmkIcon/CmkIcon.vue'
import CmkIconButton from 'cmk-ui-library/components/CmkIconButton.vue'
import CmkSlideIn from 'cmk-ui-library/components/CmkSlideIn/CmkSlideIn.vue'
import CmkSpace from 'cmk-ui-library/components/CmkSpace.vue'
import CmkHeading from 'cmk-ui-library/components/typography/CmkHeading.vue'
import CmkCheckbox from 'cmk-ui-library/components/user-input/CmkCheckbox.vue'
import usei18n from 'cmk-ui-library/lib/i18n'
import { ref } from 'vue'

import FieldComponent from '@/dashboard/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard/components/Wizard/components/TableForm/TableFormRow.vue'

import { type CustomGraphOptions } from '../api'
import { type DataFieldErrors, useCustomGraphOptions } from '../composables/useCustomGraphOptions'
import UnitSettings from './UnitSettings.vue'
import VerticalRangeSettings from './VerticalRangeSettings.vue'

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
  <CmkSlideIn :open="open" size="small" @close="closeSlideIn">
    <div class="graphing-designer-settings__area">
      <CmkHeading type="h1">{{ _t('Custom graph settings') }}</CmkHeading>
      <div class="graphing-designer-settings__close-button">
        <CmkIconButton
          name="close"
          size="small"
          data-testid="icon-x-close-button"
          @click="closeSlideIn"
        />
      </div>

      <CmkSpace direction="vertical" />

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
          <TableFormRow>
            <FieldDescription>{{ _t('Unit') }}</FieldDescription>
            <FieldComponent>
              <UnitSettings
                v-model:unit-type="graphOptions.unitType.value"
                v-model:notation="graphOptions.notation.value"
                v-model:symbol="graphOptions.symbol.value"
                v-model:rounding-mode="graphOptions.roundingMode.value"
                v-model:rounding-digits="graphOptions.roundingDigits.value"
                :digit-error="validationErrors.precision_digits ?? null"
              />
            </FieldComponent>
          </TableFormRow>
          <TableFormRow>
            <FieldDescription>{{ _t('Explicit range') }}</FieldDescription>
            <FieldComponent>
              <VerticalRangeSettings
                v-model:vertical-range-type="graphOptions.verticalRangeType.value"
                v-model:lower-bound="graphOptions.lowerVerticalRange.value"
                v-model:upper-bound="graphOptions.upperVerticalRange.value"
                :lower-bound-error="validationErrors.lower_range ?? null"
                :upper-bound-error="validationErrors.upper_range ?? null"
              />
            </FieldComponent>
          </TableFormRow>
          <TableFormRow>
            <FieldDescription>{{ _t('Metric visibility') }}</FieldDescription>
            <FieldComponent>
              <CmkCheckbox
                v-model="graphOptions.showZeroValues.value"
                :label="_t('Show zero values')"
              />
            </FieldComponent>
          </TableFormRow>
        </TableForm>
      </div>
    </div>
  </CmkSlideIn>
</template>

<style scoped>
.graphing-designer-settings__action-bar {
  display: flex;
  justify-content: flex-start;
  gap: var(--dimension-4);
}

.graphing-designer-settings__close-button {
  position: absolute;
  top: 25px;
  right: 10px;
}

.graphing-designer-settings__area {
  position: relative;
  padding: var(--dimension-8);
}

.graphing-designer-settings__block {
  padding-top: var(--dimension-10);
}

.graphing-designer-settings__fields {
  padding-top: var(--dimension-6);
}
</style>
