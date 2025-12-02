<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { type DynamicIconAppProps } from 'cmk-shared-typing/typescript/icon'

import CmkDynamicIcon from './CmkDynamicIcon.vue'

const props = defineProps<DynamicIconAppProps>()
</script>

<template>
  <CmkDynamicIcon v-bind="props" class="cmk-dynamic-icon-app__root" />
</template>

<style scoped>
.cmk-dynamic-icon-app__root,
/* We need to affect emblems which pass the inheritted class down */
/* stylelint-disable-next-line selector-pseudo-class-no-unknown */
:deep(.cmk-dynamic-icon-app__root) {
  /* this is to align with the old icon rendering */
  display: inherit;
  vertical-align: middle;
  padding: 0 2px;
}
</style>
