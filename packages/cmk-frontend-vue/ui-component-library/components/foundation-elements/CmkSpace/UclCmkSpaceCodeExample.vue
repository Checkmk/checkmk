<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from '@/components/CmkButton.vue'
import CmkSpace from '@/components/CmkSpace.vue'
</script>

<template>
  <CmkButton variant="secondary">First Element</CmkButton>
  <CmkSpace direction="horizontal" size="medium" />
  <CmkButton variant="primary">Second Element</CmkButton>
</template>
