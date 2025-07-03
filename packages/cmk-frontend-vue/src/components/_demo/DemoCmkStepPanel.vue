<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref } from 'vue'
import CmkAccordionStepPanel from '../CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
import CmkAccordionStepPanelItem from '../CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'

defineProps<{ screenshotMode: boolean }>()

const openedItems = ref<string[]>(['step-1'])
</script>

<template>
  <CmkAccordionStepPanel v-model="openedItems" class="cmk-demo-step-panel">
    <CmkAccordionStepPanelItem
      :accomplished="true"
      :step="1"
      title="Accomplished step 1"
      info="2-3 min"
    >
      Testcontent 1
    </CmkAccordionStepPanelItem>
    <CmkAccordionStepPanelItem :accomplished="false" :step="2" title="Current step 2" info="5 min">
      Testcontent 2
    </CmkAccordionStepPanelItem>
    <CmkAccordionStepPanelItem :accomplished="false" :step="3" title="Future step 3" info="&infin;">
      Testcontent 3
    </CmkAccordionStepPanelItem>
  </CmkAccordionStepPanel>

  <br /><br />
  <label>Currently opened items:</label><br /><br />
  <code>{{ openedItems }}</code>
</template>

<style scoped>
.cmk-demo-step-panel {
  width: 400px;
}
</style>
