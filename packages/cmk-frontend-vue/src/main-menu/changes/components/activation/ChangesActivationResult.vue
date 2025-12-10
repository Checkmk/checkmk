<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkAlertBox from '@/components/CmkAlertBox.vue'

const props = defineProps<{ type: 'success' | 'warning'; title: string; info: string }>()
</script>

<template>
  <div>
    <CmkAlertBox :variant="props.type" class="mm-changes-activation-result">
      <template #heading>
        {{ props.title }}
      </template>
      {{ props.info }}
    </CmkAlertBox>
  </div>
</template>

<style scoped>
.mm-changes-activation-result {
  width: 100%;
  box-sizing: border-box;
}
</style>
