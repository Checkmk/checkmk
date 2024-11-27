<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, computed, type Ref } from 'vue'
import AlertBox from '../AlertBox.vue'
import CmkButton from '../CmkButton.vue'
import { formatError } from '../CmkError'

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
  <AlertBox v-if="props.error.value !== null" variant="error">
    <strong>
      An unexpected error occurred. Reload the Page to try again. If the Problem persists, reach out
      to the Checkmk support.
    </strong>
    <CmkButton v-if="details === false" @click="details = true">Show details</CmkButton>
    <div v-else>
      <pre>{{ errorMessage }}</pre>
    </div>
  </AlertBox>
  <div v-else>
    <slot></slot>
  </div>
</template>
