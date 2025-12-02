<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type StaticIconAppProps } from 'cmk-shared-typing/typescript/icon'
import { computed } from 'vue'

import CmkIcon from './CmkIcon.vue'
import { type CmkIconProps } from './types'

const props = defineProps<StaticIconAppProps>()

const properties = computed<CmkIconProps>(() => {
  return {
    name: props.icon,
    // default value for undefined option in python is None,
    // which translated to null in typescript,
    // which uses undefined as default parameter...
    // this whole situation is not correctly covered by cmk-shared-typing
    size: props.size === null ? undefined : props.size,
    title: props.title === null ? undefined : props.title
  }
})
</script>

<template>
  <CmkIcon v-bind="properties" class="cmk-icon-app__root" />
</template>

<style scoped>
.cmk-icon-app__root {
  /* this is to align with the old icon rendering */
  display: inherit;
  vertical-align: middle;
  padding: 0 2px;
}
</style>
