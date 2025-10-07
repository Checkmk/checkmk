<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIcon from '@/components/CmkIcon.vue'

const props = defineProps<{
  validation: Array<string> | undefined
}>()
</script>

<template>
  <div
    v-if="props.validation !== undefined && props.validation.length > 0"
    class="cmk-inline-validation"
  >
    <CmkIcon name="alert-crit" variant="inline" size="large" />
    <div>
      <span v-for="message in props.validation" :key="message">{{ message }}</span>
    </div>
  </div>
</template>

<style scoped>
div.cmk-inline-validation {
  margin-top: var(--spacing);
  padding: 8px 12px;
  background-color: var(--error-msg-bg-color);
  border-radius: var(--border-radius);

  div {
    display: inline-block;
    margin-left: 7px;
  }

  span {
    display: block;
    line-height: 16px;

    &:first-child {
      margin-top: 1px;
    }
  }
}
</style>
