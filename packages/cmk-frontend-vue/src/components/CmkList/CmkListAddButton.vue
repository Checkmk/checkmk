<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import CmkButton from '@/components/CmkButton.vue'
import CmkIcon from '@/components/CmkIcon.vue'
import CmkSpace from '@/components/CmkSpace.vue'

defineProps<{
  addElementLabel: string | undefined
  addElement: () => void
}>()
</script>

<template>
  <CmkButton variant="minimal" size="small" @click.prevent="addElement">
    <CmkIcon name="plus" />
    <template v-if="addElementLabel!!">
      <CmkSpace size="small" />
      {{ addElementLabel }}
    </template>
  </CmkButton>
</template>
