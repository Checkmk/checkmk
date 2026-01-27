<!--
Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
conditions defined in the file COPYING, which is part of this source code package.
-->

<script setup lang="ts">
import { ref, watch } from 'vue'
import { type RouteRecordNormalized, RouterLink, RouterView } from 'vue-router'
import { useRoute, useRouter } from 'vue-router'

import { immediateWatch } from '@/lib/watch'

import CmkButton from '@/components/CmkButton.vue'
import CmkToggleButtonGroup from '@/components/CmkToggleButtonGroup.vue'

import router from './router'

const routes = ref<Array<RouteRecordNormalized>>([])
const crumbs = ref<Array<RouteRecordNormalized>>([])
const currentFolder = ref<string>('/')

const selectedTheme = ref<'facelift' | 'modern-dark'>('facelift')
const selectedCss = ref<'cmk' | 'none'>('cmk')

const currentRoute = useRoute()
const screenshotMode = ref(currentRoute.query.screenshot === 'true')

async function enableScreenshotMode() {
  await router.push({ path: currentRoute.path, query: { screenshot: 'true' } })
}
function changeToFolder(folder: string) {
  currentFolder.value = folder

  routes.value = router.getRoutes().filter((r) => r.meta.inFolder === folder)

  const crumbPaths = ['/']
  let path = '/'

  for (const element of currentFolder.value.split('/')) {
    if (element === '') {
      continue
    }
    path = `${path}${element}/`
    crumbPaths.push(path)
  }

  crumbs.value = crumbPaths.map((c) => router.getRoutes().filter((r) => r.path === c)[0]!)
}

useRouter().afterEach(() => {
  if (currentRoute.meta.type === 'folder') {
    changeToFolder(currentRoute.fullPath)
  } else if (currentRoute.meta.type === 'page' && !routes.value.length) {
    // if this is a page, and we just refreshed the page (no routes yet)
    const fullPath = currentRoute.fullPath
    const folder = fullPath.substring(0, fullPath.lastIndexOf('/') + 1)
    changeToFolder(folder)
  }
})

watch(
  () => currentRoute.query.screenshot,
  (screenshot) => {
    screenshotMode.value = screenshot === 'true'
  }
)

async function setTheme(name: 'modern-dark' | 'facelift') {
  document.getElementsByTagName('body')[0]!.dataset['theme'] = name
}

async function setCss(name: 'cmk' | 'none') {
  let url: string
  if (name === 'none') {
    url = ''
  } else {
    url = (await import(`~cmk-frontend/themes/${selectedTheme.value}/theme.css?url`)).default
  }
  ;(document.getElementById('cmk-theming-stylesheet') as HTMLLinkElement).href = url
}

immediateWatch(
  () => selectedCss.value,
  async (name: 'cmk' | 'none') => {
    selectedCss.value = name
    await setCss(name)
    await setTheme(selectedTheme.value)
  }
)

immediateWatch(
  () => selectedTheme.value,
  async (name: 'facelift' | 'modern-dark') => {
    selectedTheme.value = name
    await setCss(selectedCss.value)
    await setTheme(name)
  }
)
</script>

<template>
  <div v-if="!screenshotMode" class="cmk-vue-app demo-app">
    <nav>
      <fieldset>
        <legend>global styles</legend>
        <CmkToggleButtonGroup
          v-model="selectedCss"
          :options="[
            { label: 'cmk', value: 'cmk' },
            { label: 'none', value: 'none' }
          ]"
        />
        <CmkToggleButtonGroup
          v-model="selectedTheme"
          :options="[
            { label: 'light', value: 'facelift' },
            { label: 'dark', value: 'modern-dark' }
          ]"
        />
        <CmkButton @click="enableScreenshotMode">screenshot mode</CmkButton>
      </fieldset>
      <ul class="demo-app__breadcrumbs">
        <li v-for="crumb in crumbs" :key="crumb.path">
          <RouterLink :to="crumb.path">{{ crumb.meta.name }}/</RouterLink>
        </li>
      </ul>
      <ul>
        <li v-for="route in routes" :key="route.path">
          <RouterLink :to="route.path" :class="`demo-app__nav-${route.meta.type}`">
            <span v-if="route.meta.type === 'folder'">🗀</span>{{ route.meta.name }}
          </RouterLink>
        </li>
      </ul>
    </nav>
    <main>
      <h1>{{ currentRoute.meta.name }}</h1>
      <div class="demo-app__area">
        <RouterView />
      </div>
    </main>
  </div>
  <RouterView v-else />
</template>

<style scoped>
.demo-app {
  display: flex;
  color: var(--font-color);
  background-color: var(--default-bg-color);
  height: 100vh;
  padding: 10px 10px 10px 0;

  main {
    h1 {
      color: inherit;
    }

    height: fit-content;

    .demo-app__area {
      padding: 1em;
      border: 2px solid var(--default-form-element-bg-color);
      background-color: var(--default-component-bg-color);
    }
  }

  nav {
    margin: 0 1em 0 0;

    ul {
      list-style: none;
      padding: 0;

      li {
        margin: 0.2em 0;

        /* stylelint-disable-next-line checkmk/vue-bem-naming-convention */
        a.demo-app__nav-page.router-link-exact-active {
          font-weight: bold;
        }
      }
    }
  }

  ul.demo-app__breadcrumbs {
    a {
      color: inherit;
    }

    & > li {
      display: inline;
      margin: 0;
      padding: 0;

      & > a {
        padding: 0;
        padding-right: 0.3em;
      }
    }
  }

  fieldset {
    /* stylelint-disable-next-line selector-pseudo-class-no-unknown */
    :deep(button) {
      min-width: 50px;
    }
  }
}
</style>
