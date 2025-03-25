<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from './CmkButton.vue'
import CmkIcon from './CmkIcon.vue'
</script>

<template>
  <CmkButton><CmkIcon variant="inline" name="cancel" /><slot /></CmkButton>
</template>
