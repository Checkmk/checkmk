<!--
Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkScrollContainer from '@/components/CmkScrollContainer.vue'
</script>

<template>
  <CmkScrollContainer max-height="200px" type="outer">
    <p>
      Long content that will cause the container to overflow and display the custom "outer" style
      scrollbar.
    </p>
  </CmkScrollContainer>
</template>
