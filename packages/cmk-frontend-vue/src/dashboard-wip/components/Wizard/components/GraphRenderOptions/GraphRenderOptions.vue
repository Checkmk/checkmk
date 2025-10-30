<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { computed } from 'vue'

import usei18n from '@/lib/i18n'

import CmkDropdown from '@/components/CmkDropdown'
import CmkIndent from '@/components/CmkIndent.vue'
import CmkLabel from '@/components/CmkLabel.vue'
import type { Suggestion } from '@/components/CmkSuggestions'
import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'

import FieldComponent from '@/dashboard-wip/components/Wizard/components/TableForm/FieldComponent.vue'
import FieldDescription from '@/dashboard-wip/components/Wizard/components/TableForm/FieldDescription.vue'
import TableForm from '@/dashboard-wip/components/Wizard/components/TableForm/TableForm.vue'
import TableFormRow from '@/dashboard-wip/components/Wizard/components/TableForm/TableFormRow.vue'

import ColorSelector from '../ColorSelector/ColorSelector.vue'

const { _t } = usei18n()

interface GraphRenderOptions {
  colorOptions?: Suggestion[]
}

const { colorOptions = [] } = defineProps<GraphRenderOptions>()

const horizontalAxis = defineModel<boolean>('horizontalAxis', { required: true })
const verticalAxis = defineModel<boolean>('verticalAxis', { required: true })
const verticalAxisWidthMode = defineModel<'fixed' | 'absolute'>('verticalAxisWidthMode', {
  required: true
})
const fixedVerticalAxisWidth = defineModel<number>('fixedVerticalAxisWidth', { required: true })

const fontSize = defineModel<number>('fontSize', { required: true })
const color = defineModel<string>('color', { required: false, default: undefined })
const timestamp = defineModel<boolean>('timestamp', { required: true })
const roundMargin = defineModel<boolean>('roundMargin', { required: true })
const graphLegend = defineModel<boolean>('graphLegend', { required: true })

const clickToPlacePin = defineModel<boolean>('clickToPlacePin', { required: true })
const showBurgerMenu = defineModel<boolean>('showBurgerMenu', { required: true })
const dontFollowTimerange = defineModel<boolean>('dontFollowTimerange', { required: true })

const displayColorChooser = computed(() => color.value !== undefined && colorOptions.length > 0)
</script>

<template>
  <TableForm>
    <TableFormRow>
      <FieldDescription>{{ _t('Axis') }}</FieldDescription>
      <FieldComponent>
        <div>
          <CmkCheckbox v-model:model-value="horizontalAxis" :label="_t('Horizontal axis')" />
        </div>
        <div>
          <CmkCheckbox v-model:model-value="verticalAxis" :label="_t('Vertical axis')" />
          <CmkIndent>
            <CmkDropdown
              :selected-option="verticalAxisWidthMode"
              :label="_t('Select option')"
              :options="{
                type: 'fixed',
                suggestions: [
                  { name: 'fixed', title: _t('Use fixed width (relative to font size)') },
                  { name: 'absolute', title: _t('Use absolute width:') }
                ]
              }"
              @update:selected-option="
                (value) => {
                  verticalAxisWidthMode = value === 'fixed' ? 'fixed' : 'absolute'
                }
              "
            />

            <CmkInput
              v-if="verticalAxisWidthMode === 'absolute'"
              v-model:model-value="fixedVerticalAxisWidth as number"
              type="number"
            />
          </CmkIndent>
        </div>
      </FieldComponent>
    </TableFormRow>

    <TableFormRow>
      <FieldDescription>{{ _t('Graph styling') }}</FieldDescription>
      <FieldComponent>
        <div>
          <CmkLabel>{{ _t('Font size') }}</CmkLabel>
          <CmkIndent>
            <CmkInput v-model:model-value="fontSize as number" type="number" />
          </CmkIndent>
        </div>

        <div v-if="displayColorChooser">
          <CmkLabel>{{ _t('Color') }}</CmkLabel>
          <CmkIndent>
            <ColorSelector v-model:color="color" :static-options="colorOptions" />
          </CmkIndent>
        </div>
        <div>
          <CmkCheckbox
            v-model:model-value="timestamp"
            :label="_t('Date and time stamp (right upper corner)')"
          />
        </div>
        <div>
          <CmkCheckbox v-model:model-value="roundMargin" :label="_t('Margin round the graph')" />
        </div>
        <div>
          <CmkCheckbox v-model:model-value="graphLegend" :label="_t('Graph legend')" />
        </div>
      </FieldComponent>
    </TableFormRow>

    <TableFormRow>
      <FieldDescription>{{ _t('Interaction') }}</FieldDescription>
      <FieldComponent>
        <div>
          <CmkCheckbox
            v-model:model-value="clickToPlacePin"
            :label="_t('Click on graph to place pin')"
          />
        </div>
        <div>
          <CmkCheckbox
            v-model:model-value="showBurgerMenu"
            :label="_t('Show burger menu for graph options')"
          />
        </div>
      </FieldComponent>
    </TableFormRow>

    <TableFormRow>
      <FieldDescription>{{ _t('Time range synchronization') }}</FieldDescription>
      <FieldComponent>
        <CmkCheckbox
          v-model:model-value="dontFollowTimerange"
          :label="_t('Do not follow timerange changes of other graphs on the current dashboard')"
        />
      </FieldComponent>
    </TableFormRow>
  </TableForm>
</template>
