/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

// this is the main entrypoint for loading the auto hot reload version of vue
// frontend. this file will also be shipped with the regular checkmk build, as
// we have a global option to activate this feature.

console.log('cmk-frontend-vue stage 1')

let errors = 0

function loadScript(url: string, fallback: boolean = false) {
  const script = document.createElement('script')
  if (fallback === false) {
    script.type = 'module'
    script.onerror = scriptOnError
  }
  script.src = url
  document.head.appendChild(script)
}

function scriptOnError(event: string | Event) {
  errors += 1
  if (errors === 1) {
    // when we see the first error, we fall back:
    console.error('cmk-frontend-vue stage 1: could not load stage 2 scripts:')
    console.error(event)
    alert(
      "vite client can not be loaded.\nStart vite dev server and access this site through the dev server or deactivate 'Inject frontend_vue files via vite client' in global options."
    )

    const entrypointScript = document.querySelectorAll<HTMLFormElement>(
      'script[type="cmk-entrypoint-vue-stage1"]'
    )

    if (entrypointScript.length !== 1) {
      throw Error(`Found ${entrypointScript.length} cmk-entrypoint-vue-stage1 scripts`)
    }

    const scriptContent = entrypointScript[0]!.textContent
    if (scriptContent === null) {
      throw Error(`Found cmk-entrypoint-vue-stage1 script is empty`)
    }

    const data = JSON.parse(scriptContent)
    data.fallback.forEach((url: string) => {
      console.info(`Loading ${url} as fallback`)
      loadScript(url, true)
    })
  }
}

const scriptsToLoad = ['/cmk-frontend-vue-ahr/@vite/client', '/cmk-frontend-vue-ahr/src/main.ts']

scriptsToLoad.forEach(function (url: string) {
  loadScript(url)
})
