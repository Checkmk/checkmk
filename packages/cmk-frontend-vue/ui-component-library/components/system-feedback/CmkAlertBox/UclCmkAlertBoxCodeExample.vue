<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkAlertBox from '@/components/CmkAlertBox.vue'

const isAlertOpen = ref(true)
</script>

<template>
  <CmkAlertBox v-model:open="isAlertOpen" variant="info" size="medium" heading="Alert Heading">
    This is an important alert message that requires your attention.
  </CmkAlertBox>
</template>
