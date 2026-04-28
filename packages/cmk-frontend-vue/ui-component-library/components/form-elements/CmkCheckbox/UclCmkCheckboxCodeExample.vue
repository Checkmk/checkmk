<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkCheckbox from '@/components/user-input/CmkCheckbox.vue'

const isChecked = ref(false)
</script>

<template>
  <CmkCheckbox
    v-model="isChecked"
    label="Enable notifications"
    help="You will receive alerts via email."
  />
</template>
