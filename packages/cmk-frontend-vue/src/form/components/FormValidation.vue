<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
const props = defineProps<{
  validation: Array<string>
}>()
</script>

<template>
  <div v-if="props.validation.length > 0" class="form-validation">
    <div class="form-validation__icon" />
    <div>
      <span v-for="message in props.validation" :key="message">{{ message }}</span>
    </div>
  </div>
</template>

<style scoped>
div.form-validation {
  margin-top: 12px;
  padding: 8px 12px;
  background-color: var(--error-msg-bg-color);
  border-radius: var(--border-radius);

  div {
    display: inline-block;
    margin-right: 12px;
    vertical-align: top;
  }

  div.form-validation__icon {
    width: 18px;
    height: 18px;
    background-size: 18px;
    background-image: var(--icon-alert-crit);
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
