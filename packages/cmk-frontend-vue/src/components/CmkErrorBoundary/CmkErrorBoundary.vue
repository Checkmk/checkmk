<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type Ref } from 'vue'

import CmkErrorAlert from './CmkErrorAlert.vue'

const props = defineProps<{ error: Ref<Error | null> }>()
</script>

<template>
  <CmkErrorAlert v-if="props.error.value !== null" :error="props.error.value" />
  <template v-else>
    <slot> </slot>
  </template>
</template>
