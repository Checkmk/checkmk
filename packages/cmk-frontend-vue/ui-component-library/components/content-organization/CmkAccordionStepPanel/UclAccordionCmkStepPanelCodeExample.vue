<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkAccordionStepPanel from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanel.vue'
import CmkAccordionStepPanelItem from '@/components/CmkAccordionStepPanel/CmkAccordionStepPanelItem.vue'

const openSteps = ref(['step-2'])
</script>

<template>
  <CmkAccordionStepPanel v-model="openSteps">
    <CmkAccordionStepPanelItem :step="1" title="Download Agent" info="2-3 min" :accomplished="true">
      <p>Select your operating system and download the appropriate agent package.</p>
    </CmkAccordionStepPanelItem>

    <CmkAccordionStepPanelItem :step="2" title="Install Package" info="5 min" :accomplished="false">
      <p>Run the installer on your target machine. Ensure you have root/admin privileges.</p>
    </CmkAccordionStepPanelItem>
  </CmkAccordionStepPanel>
</template>
