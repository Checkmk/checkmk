<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from '../CmkButton.vue'
import { getWizardContext } from '@/components/CmkWizard/utils.ts'

export interface CmkWizardButtonProps {
  type: 'next' | 'previous' | 'finish'
}

const context = getWizardContext()
const props = defineProps<CmkWizardButtonProps>()

function onClick() {
  switch (props.type) {
    case 'next':
      context.navigation.next()
      break
    case 'previous':
      context.navigation.prev()
      break
  }
}
</script>

<template>
  <CmkButton @click="onClick"> {{ props.type }} </CmkButton>
</template>

<style scoped></style>
