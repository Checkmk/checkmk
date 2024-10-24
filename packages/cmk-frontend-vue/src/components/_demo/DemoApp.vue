<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, ref } from 'vue'
import { immediateWatch } from '@/form/components/utils/watch'
import ToggleButtonGroup from '@/components/ToggleButtonGroup.vue'
import router from './router'

import { filterRoutes } from './utils'

const routes = computed(() => {
  return filterRoutes(router.getRoutes(), '')
})

const selectedTheme = ref<'facelift' | 'modern-dark'>('facelift')
const selectedCss = ref<'cmk' | 'none'>('cmk')

async function setTheme(name: 'modern-dark' | 'facelift') {
  document.getElementsByTagName('body')[0]!.dataset['theme'] = name
}

async function setCss(name: 'cmk' | 'none') {
  let url: string
  if (name === 'none') {
    url = ''
  } else {
    url = (await import(`~cmk-frontend/src/themes/${selectedTheme.value}/theme.scss?url`)).default
  }
  ;(document.getElementById('cmk-theming-stylesheet') as HTMLLinkElement).href = url
}

immediateWatch(
  () => selectedCss.value,
  (name: 'cmk' | 'none') => {
    selectedCss.value = name
    setCss(name)
    setTheme(selectedTheme.value)
  }
)

immediateWatch(
  () => selectedTheme.value,
  (name: 'facelift' | 'modern-dark') => {
    selectedTheme.value = name
    setCss(selectedCss.value)
    setTheme(name)
  }
)
</script>

<template>
  <div class="demo">
    <nav>
      <fieldset>
        <legend>global styles</legend>
        <ToggleButtonGroup
          v-model="selectedCss"
          :options="[
            { label: 'cmk', value: 'cmk' },
            { label: 'none', value: 'none' }
          ]"
        />
        <ToggleButtonGroup
          v-model="selectedTheme"
          :options="[
            { label: 'light', value: 'facelift' },
            { label: 'dark', value: 'modern-dark' }
          ]"
        />
      </fieldset>
      <ul>
        <li v-for="route in routes" :key="route.path">
          <RouterLink :to="route.path">{{ route.name }}</RouterLink>
        </li>
      </ul>
    </nav>
    <main>
      <h1>{{ $route.name }}</h1>
      <div class="demo-area">
        <RouterView />
      </div>
    </main>
  </div>
</template>

<style scoped>
* {
  padding: 10px;
}
.demo {
  display: flex;
  color: var(--default-text-color);
  background-color: var(--default-bg-color);
  height: 100vh;

  main {
    h1 {
      color: inherit;
    }
    height: fit-content;
    border: 2px solid var(--default-form-element-bg-color);
    background-color: var(--default-component-bg-color);
    border-radius: 5px;
    .demo-area {
      padding: 1em;
    }
  }
  nav {
    margin: 0 1em;
    ul {
      list-style: none;
      padding: 0;
      li {
        margin: 0.5em 0;
      }
    }
    a {
      color: inherit;
    }
  }
  fieldset {
    :deep(button) {
      min-width: 50px;
    }
  }
}
</style>
