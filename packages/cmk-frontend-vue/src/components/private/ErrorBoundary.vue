<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, computed, type Ref } from 'vue'
import CmkAlertBox from '../CmkAlertBox.vue'
import CmkButton from '../CmkButton.vue'
import { formatError } from '@/lib/error.ts'

const details = ref<boolean>(false)

const errorMessage = computed<string>(() => {
  const error = props.error.value
  if (error === null) {
    return ''
  }
  return formatError(error)
})

const props = defineProps<{ error: Ref<Error | null> }>()
</script>

<template>
  <CmkAlertBox v-if="props.error.value !== null" variant="error">
    <div>
      An unknown error occurred.<br />
      Refresh the page to try again. If the problem persists, reach out to the Checkmk support.
    </div>
    <CmkButton v-if="details === false" @click="details = true">Show details</CmkButton>
    <div v-else>
      <pre>{{ errorMessage }}</pre>
    </div>
  </CmkAlertBox>
  <div v-else style="height: 100%">
    <slot></slot>
  </div>
</template>
