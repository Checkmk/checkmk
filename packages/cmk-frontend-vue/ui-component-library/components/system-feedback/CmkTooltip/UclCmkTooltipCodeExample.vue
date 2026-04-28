<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkButton from '@/components/CmkButton'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from '@/components/CmkTooltip'

const isTooltipOpen = ref(false)
</script>

<template>
  <CmkTooltipProvider>
    <CmkTooltip v-model:open="isTooltipOpen">
      <CmkTooltipTrigger as-child>
        <CmkButton variant="secondary">Interact with me</CmkButton>
      </CmkTooltipTrigger>

      <CmkTooltipContent side="top" align="center">
        <div class="tooltip-content">This is a tooltip on the top!</div>
      </CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
</template>
