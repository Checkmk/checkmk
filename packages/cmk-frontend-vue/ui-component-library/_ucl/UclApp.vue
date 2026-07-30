<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'

import UclHeader from './components/UclHeader.vue'
import UclNavigation from './components/UclNavigation.vue'
import { useLegacyCss } from './composables/useLegacyCss'

useLegacyCss()

const currentRoute = useRoute()
const screenshotMode = ref(currentRoute.query.screenshot === 'true')
const BUILD_COMMIT = import.meta.env.VITE_BUILD_COMMIT

watch(
  () => currentRoute.query.screenshot,
  (screenshot) => {
    screenshotMode.value = screenshot === 'true'
  }
)
</script>

<template>
  <div v-if="!screenshotMode" class="cmk-vue-app ucl">
    <header class="ucl-app__header">
      <UclHeader />
    </header>

    <div class="ucl-app__body">
      <aside class="ucl-app__sidebar" aria-label="Component navigation">
        <UclNavigation />
      </aside>

      <main id="content_area" class="ucl-app__main">
        <div class="ucl-app__area">
          <RouterView />
        </div>

        <div class="ucl-app__footer-build-info">
          <ul>
            <li v-if="BUILD_COMMIT">
              Built from commit <code>{{ BUILD_COMMIT }}</code>
            </li>
            <li v-else><i>Commit of this build is not known.</i></li>
          </ul>
        </div>
      </main>
    </div>
  </div>
  <RouterView v-else />
</template>

<style scoped>
.ucl-app {
  display: flex;
  flex-direction: column;
  color: var(--ucl-body-text-color);
  background-color: var(--ucl-app-bg-color);
  height: 100vh;
}

.ucl-app__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 24px;
  background-color: var(--ucl-header-bg-color);
  border-bottom: 1px solid var(--ucl-elements-border-color);
  height: 50px;
}

.ucl-app__body {
  display: flex;
  flex: 1;
  padding: 16px;
  gap: 16px;
}

.ucl-app__sidebar {
  display: flex;
  flex-direction: column;
  width: 250px;
  border-right: 1px solid var(--ucl-elements-border-color);
  flex-shrink: 0;
}

.ucl-app__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.ucl-app__area {
  flex: 1;
  padding: 16px;
}

.ucl-app__footer-build-info {
  padding: 16px 0 0;
  margin: 16px;
  color: var(--ucl-footer-text-color);
  border-top: 1px solid var(--ucl-elements-border-color);

  ul {
    list-style-type: none;
    margin: 0;
    padding: 0;

    li {
      float: left;
      margin-right: 2em;

      code {
        font-family: monospace;
      }
    }
  }
}
</style>
