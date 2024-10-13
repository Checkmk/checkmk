<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import router from './router'

const routes = computed(() => {
  return router.getRoutes()
})

function setTheme(name: 'modern-dark' | 'facelift') {
  document.getElementsByTagName('body')[0]!.dataset['theme'] = name
}

onMounted(() => {
  setTheme('facelift')
})
</script>

<template>
  <div class="demo">
    <nav>
      <button @click="setTheme('modern-dark')">dark</button>
      <button @click="setTheme('facelift')">light</button>
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
  background-color: var(--default-background-color);
  height: 100vh;

  main {
    h1 {
      color: inherit;
    }
    height: fit-content;
    border: 2px solid var(--default-select-background-color);
    background-color: var(--default-component-background-color);
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
}
</style>
