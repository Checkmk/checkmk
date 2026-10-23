<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from 'cmk-ui-library/components/CmkButton'
import CmkTooltip, {
  CmkTooltipContent,
  CmkTooltipProvider,
  CmkTooltipTrigger
} from 'cmk-ui-library/components/CmkTooltip'
import { ref } from 'vue'

const isTooltipOpen = ref(false)
</script>

<template>
  <CmkTooltipProvider>
    <CmkTooltip v-model:open="isTooltipOpen">
      <CmkTooltipTrigger as-child>
        <CmkButton variant="secondary">Interact with me</CmkButton>
      </CmkTooltipTrigger>

      <CmkTooltipContent side="top" align="center" variant="text">
        This is a tooltip on the top!
      </CmkTooltipContent>
    </CmkTooltip>
  </CmkTooltipProvider>
</template>
