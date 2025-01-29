<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->
<script setup lang="ts">
// TODO: move this file CMK-19774
import CmkAlertBox from '@/components/CmkAlertBox.vue'
import { computed } from 'vue'
import router from './router'
import { filterRoutes } from './utils'

defineProps<{ screenshotMode: boolean }>()

const routes = computed(() => {
  return filterRoutes(router.getRoutes(), '/form')
})
</script>

<template>
  <template v-if="!screenshotMode">
    <CmkAlertBox variant="warning">
      <h2>Attention: No real Building-Blocks here!</h2>
      <p>
        This is just a demo for FormEdit, but you should use FormEdit only in combination with its
        backend/python counterpart. Don't start writing specs in JavaScript!
      </p>
    </CmkAlertBox>
    <ul>
      <li v-for="route in routes" :key="route.path">
        <RouterLink :to="route.path">{{ route.name }}</RouterLink>
      </li>
    </ul>
    <hr />
  </template>
  <RouterView :screenshot-mode="screenshotMode" />
</template>
