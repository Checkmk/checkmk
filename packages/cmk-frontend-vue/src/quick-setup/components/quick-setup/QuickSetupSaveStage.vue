<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import type { QuickSetupSaveStageProps } from '@/quick-setup/components/quick-setup/quick_setup_types'
import QuickSetupStageContent from './QuickSetupStageContent.vue'

defineProps<QuickSetupSaveStageProps>()
</script>

<template>
  <div class="qs-save-stage__content">
    <QuickSetupStageContent
      :index="index"
      :number-of-stages="numberOfStages"
      :loading="loading"
      :errors="errors"
      :mode="mode"
      :buttons="buttons"
      :content="content || null"
    />
  </div>
</template>

<style scoped>
.qs-save-stage__content {
  padding-left: 6.8rem;
}
</style>
