<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
import { type DialogWidgetProps } from './widget_types'
import CmkDialog from '@/components/CmkDialog.vue'

const props = defineProps<DialogWidgetProps>()
</script>

<template>
  <div>
    <CmkDialog :message="props.text" />
  </div>
</template>
