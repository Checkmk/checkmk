<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
defineProps<{
  labelSource: 'discovered' | 'explicit' | 'ruleset' | null
  value: string
}>()
</script>

<template>
  <div class="form-labels-label" :class="[`form-labels-label--${labelSource}`]">{{ value }}</div>
</template>

<style scoped>
.form-labels-label {
  width: fit-content;
  margin: 0 5px 0 0;
  padding: 1px 4px;
  border-radius: 5px;

  &:first-child {
    margin-left: 0;
  }
  &.form-labels-label--null {
    background-color: var(--tag-color);
    color: var(--black);
  }
  &.form-labels-label--discovered {
    background-color: var(--tag-discovered-color);
    color: var(--black);
  }
  &.form-labels-label--explicit {
    background-color: var(--tag-explicit-color);
    color: var(--white);
  }
  &.form-labels-label--ruleset {
    background-color: var(--tag-ruleset-color);
    color: var(--white);
  }
}
</style>
