<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkLabel from '@/components/CmkLabel.vue'
import CmkInput from '@/components/user-input/CmkInput.vue'
import CmkLabelRequired from '@/components/user-input/CmkLabelRequired.vue'

defineProps<{ screenshotMode: boolean }>()
</script>

<template>
  <CmkLabel>
    Choose a name
    <CmkLabelRequired />
  </CmkLabel>
  <CmkInput type="text" field-size="MEDIUM" />
</template>
