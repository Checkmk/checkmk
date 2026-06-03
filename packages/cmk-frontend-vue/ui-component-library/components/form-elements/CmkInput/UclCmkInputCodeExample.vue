<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkInput from '@/components/user-input/CmkInput.vue'

const username = ref('')
</script>

<template>
  <CmkInput v-model="username" type="text" field-size="medium" />
</template>
