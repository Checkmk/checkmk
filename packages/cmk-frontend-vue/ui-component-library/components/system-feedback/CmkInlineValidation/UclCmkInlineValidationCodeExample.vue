<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { ref } from 'vue'

import CmkInlineValidation from '@/components/user-input/CmkInlineValidation.vue'

const formErrors = ref<string[]>([
  'This is an inline validation error message.',
  'A secondary validation condition also failed.'
])
</script>

<template>
  <CmkInlineValidation :validation="formErrors" />
</template>
