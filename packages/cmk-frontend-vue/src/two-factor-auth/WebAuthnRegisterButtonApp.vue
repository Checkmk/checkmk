<!--
Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<template>
  <div></div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

import { register } from './webauthn'

const handleWebauthnRegister = () => {
  register().catch((error) => {
    console.error(error)
  })
}

onMounted(() => {
  document.addEventListener('cmk-webauthn-register-button', handleWebauthnRegister)
})

onUnmounted(() => {
  document.removeEventListener('cmk-webauthn-register-button', handleWebauthnRegister)
})
</script>
