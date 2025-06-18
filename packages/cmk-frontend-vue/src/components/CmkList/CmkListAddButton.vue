<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import FormButton from '@/form/components/forms/FormButton.vue'
import CmkIconButton from '@/components/CmkIconButton.vue'

defineProps<{
  addElementLabel: string | undefined
  addElement: () => void
}>()
</script>

<template>
  <FormButton v-if="addElementLabel!!" @click="addElement">
    {{ addElementLabel }}
  </FormButton>
  <CmkIconButton v-else name="plus" @click="addElement" />
</template>
