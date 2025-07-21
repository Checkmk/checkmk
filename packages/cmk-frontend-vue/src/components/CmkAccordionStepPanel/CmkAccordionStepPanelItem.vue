<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkBadge from '../CmkBadge.vue'
import CmkIcon from '../CmkIcon.vue'
import CmkChip from '../CmkChip.vue'
import CmkAccordionItemStateIndicator from '../CmkAccordion/CmkAccordionItemStateIndicator.vue'
import { computed } from 'vue'
import CmkAccordionItem from '../CmkAccordion/CmkAccordionItem.vue'
import CmkHeading from '../typography/CmkHeading.vue'

export interface CmkAccordionStepPanelItemProps {
  accomplished?: boolean | undefined
  disabled?: boolean | undefined
  step: number
  title: string
  info?: string
}

const props = defineProps<CmkAccordionStepPanelItemProps>()

const value = computed(() => 'step-'.concat(props.step.toString()))
</script>

<template>
  <CmkAccordionItem :value="value" :disabled="disabled">
    <template #header>
      <CmkBadge
        size="small"
        color="success"
        type="fill"
        shape="circle"
        class="cmk-step-panel-item-indicator"
      >
        <CmkIcon v-if="props.accomplished" name="checkmark"></CmkIcon>
        <span v-if="!props.accomplished">{{ props.step.toString() }}</span></CmkBadge
      >
      <CmkAccordionItemStateIndicator
        v-if="!disabled"
        :value="value"
        class="cmk-accordion-item-state-indicator"
      />
      <CmkHeading type="h3">
        {{ title }}
      </CmkHeading>
      <CmkChip
        v-if="props.info"
        size="medium"
        variant="fill"
        :content="props.info"
        class="cmk-step-panel-item-info"
      ></CmkChip>
    </template>
    <template #content>
      <slot />
    </template>
  </CmkAccordionItem>
</template>

<style scoped>
.cmk-step-panel-item-indicator {
  margin: 0 6px 0 0;
  font-weight: normal;
}

.cmk-accordion-item-state-indicator {
  margin-right: 4px;
}

.cmk-step-panel-item-info {
  font-weight: normal;
  margin-left: auto;
}
</style>
