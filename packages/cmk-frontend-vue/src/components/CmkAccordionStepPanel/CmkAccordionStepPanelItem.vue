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
  <CmkAccordionItem :value="value">
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
      <b class="cmk-step-panel-item-title">
        {{ title }}
        <CmkAccordionItemStateIndicator :value="value"></CmkAccordionItemStateIndicator>
      </b>
      <CmkChip
        v-if="props.info"
        size="small"
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
  margin: 0 8px 0 0;
  font-weight: normal;
}

.cmk-step-panel-item-title {
  flex-grow: 2;
  text-align: left;
}

.cmk-step-panel-item-info {
  margin: 0 0 0 8px;
  font-weight: normal;
}
</style>
