<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
/**
 * @TODO This is only an example to open the workflow.
 */
import { ref } from 'vue'

import usei18n from '@/lib/i18n'

import AddWidgetDialog from './StarterDialog/AddWidgetDialog.vue'
import { dashboardWidgetWorkflows } from './WidgetWorkflowTypes'

const { _t } = usei18n()
const openDialog = ref(false)

function handleSelect(id: string) {
  openDialog.value = false
  console.log(`Start workflow with id: ${id}`)
  // @TODO check if workflow requires CEE or if it is part of CRE
  // @TODO start the workflow by opening the corresponding component
}
</script>

<template>
  <div>
    <button @click="openDialog = true">{{ _t('Add Widget') }}</button>
    <AddWidgetDialog
      :open="openDialog"
      :workflow-items="dashboardWidgetWorkflows"
      @close="openDialog = false"
      @select="handleSelect"
    />
  </div>
</template>
