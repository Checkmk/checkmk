<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'

const props = defineProps<{ type: 'success' | 'warning'; title: string; info: string }>()
</script>

<template>
  <div>
    <div class="mm-changes-activation-result">
      <CmkIcon v-if="props.type === 'success'" variant="plain" size="xxlarge" name="save" />
      <CmkIcon
        v-if="props.type === 'warning'"
        variant="plain"
        size="xxlarge"
        name="validation-error"
      />
      <span class="mm-changes-activation-result__title">{{ props.title }}</span>

      <span>{{ props.info }}</span>
    </div>
  </div>
</template>

<style scoped>
.mm-changes-activation-result {
  display: flex;
  padding: 0 29px;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 8px;
  align-self: stretch;
}

.mm-changes-activation-result__title {
  font-weight: var(--font-weight-bold);
}
</style>
