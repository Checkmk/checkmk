<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkIconButton from '@/components/CmkIconButton.vue'

const handleClick = () => {
  console.log('Button clicked!')
}
</script>

<template>
  <CmkIconButton name="main-help" size="medium" title="Get Help" @click="handleClick" />
</template>
