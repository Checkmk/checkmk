<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import usei18n from '@/lib/i18n'

import CmkIndent from '@/components/CmkIndent.vue'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'

import { ElementSelection } from '../../types'

const { _t } = usei18n()

interface GenericHolderProps {
  singleElementsLabel?: string
  multipleElementsLabel?: string
}

const props = withDefaults(defineProps<GenericHolderProps>(), {
  singleElementsLabel: '',
  multipleElementsLabel: ''
})

const modeSelection = defineModel<ElementSelection>('modeSelection', {
  default: ElementSelection.SPECIFIC
})

const _updateSelection = (value: string) => {
  modeSelection.value = value === 'SINGLE' ? ElementSelection.SPECIFIC : ElementSelection.MULTIPLE
}
</script>

<template>
  <ToggleButtonGroup
    :model-value="modeSelection"
    :options="[
      { label: props.singleElementsLabel || _t('Specific host'), value: ElementSelection.SPECIFIC },
      {
        label: props.multipleElementsLabel || _t('Multiple hosts'),
        value: ElementSelection.MULTIPLE
      }
    ]"
    @update:model-value="_updateSelection"
  />
  <CmkIndent>
    <slot v-if="modeSelection === ElementSelection.SPECIFIC" name="specific" />
    <slot v-if="modeSelection === ElementSelection.MULTIPLE" name="multi" />
  </CmkIndent>
</template>
