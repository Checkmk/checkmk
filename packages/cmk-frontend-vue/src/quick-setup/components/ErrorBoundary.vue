<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import AlertBox from './AlertBox.vue'

const error = ref<Error | null>(null)

onErrorCaptured((err: Error): boolean => {
  console.error(err)
  error.value = err
  return false
})
</script>

<template>
  <AlertBox v-if="error" variant="error"
    >An unexpected error ocurred. Please try again later</AlertBox
  >
  <div v-else><slot></slot></div>
</template>
