/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import vue from '@vitejs/plugin-vue'
import fs from 'node:fs'
import path from 'node:path'
import { type RollupLog } from 'rollup'
import { type Plugin, type UserConfig, defineConfig } from 'vite'
import VueDevTools from 'vite-plugin-vue-devtools'

// Workaround for https://github.com/vitejs/vite/issues/21955
// should be removed once the issue is closed
function bazelManifestPathFix(): Plugin {
  return {
    name: 'bazel-manifest-path-fix',
    apply: 'build',
    closeBundle() {
      const manifestPath = path.resolve('./dist/.manifest.json')
      if (!fs.existsSync(manifestPath)) return
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8')) as Record<
        string,
        { src?: string }
      >
      const strip = (s: string) => s.replace(/^.*?packages\/cmk-frontend-vue\//, '')
      const fixed: typeof manifest = {}
      for (const [key, entry] of Object.entries(manifest)) {
        if (entry.src) entry.src = strip(entry.src)
        fixed[strip(key)] = entry
      }
      fs.writeFileSync(manifestPath, JSON.stringify(fixed, null, 2))
    }
  }
}

// https://vitejs.dev/config/
export default defineConfig(({ command }) => {
  const resultBuild: UserConfig = {
    clearScreen: false,
    plugins: [
      bazelManifestPathFix(),
      vue({
        template: {
          transformAssetUrls: {
            // don't convert images to ESM imports
            // https://github.com/vitejs/vite-plugin-vue/blob/69397c2bc5924/packages/plugin-vue/README.md#asset-url-handling
            img: [],
            video: [],
            image: []
          },
          compilerOptions: {
            isCustomElement: (tag) => tag.startsWith('cmk-')
          }
        }
      })
    ],
    resolve: {
      alias: {
        '@': path.resolve('./src'),
        '@ucl': path.resolve('./ui-component-library'),
        // This is only a temporary hack to allow resolving icons and the demo css. Do not use this in new code!
        '~cmk-frontend': path.resolve('../cmk-frontend/dist')
      }
    },
    build: {
      manifest: '.manifest.json',
      sourcemap: true,
      rollupOptions: {
        onwarn: function (message: string | RollupLog) {
          if (typeof message === 'object') {
            if (message.code === 'PLUGIN_TIMINGS') {
              return
            }
            if (message.code === 'CIRCULAR_DEPENDENCY') {
              const external_circular_dependency = message.ids!.filter((id: any) =>
                id.includes('/node_modules/')
              )
              if (external_circular_dependency.length === message.ids!.length) {
                // its a circular dependency completely in node_modules folder, so we ignore it
                return
              }
            }
            console.warn(message.message)

            // vue3-gettext uses node to extract gettext strings, but we need the module
            // as a runtime module as well (not the node part though), so we let this pass
            if (
              message.message &&
              message.message.includes(
                'Module "fs" has been externalized for browser compatibility'
              ) &&
              message.message.includes('pofile/lib/po.js')
            ) {
              return
            }
          } else {
            console.warn(message)
          }
          if (command === 'build') {
            throw new Error('no warnings allowed!')
          }
        },
        input: {
          'main.js': './src/main.ts',
          'stage1.js': './src/stage1.ts'
        }
      }
    },
    base: ''
  }
  if (command === 'build') {
    return resultBuild
  } else {
    console.log(command)
    // we are in serve mode here, supporting auto hot reload
    return {
      ...resultBuild,
      plugins: [
        ...(resultBuild.plugins ?? []),
        ...(!process.env.VITEST
          ? [VueDevTools({ componentInspector: true, appendTo: /main\.ts$/ })]
          : [])
      ],
      test: {
        // enable jest-like global test APIs
        globals: true,
        environment: 'jsdom',
        setupFiles: ['tests/setup-tests.ts'],
        reporters: process.env.XML_OUTPUT_FILE // variable set by bazel
          ? [
              [
                'junit',
                {
                  outputFile: process.env.XML_OUTPUT_FILE,
                  // Hardcode the package name as prefix so that it appears in the test reporter
                  // produced by Jenkins JUnit plugin
                  classnameTemplate: ({ filename }: { filename: string }) =>
                    `//packages/cmk-frontend-vue:${filename.replace(/\//g, '.').replace(/\.test\.ts$/, '')}`
                }
              ],
              'default'
            ]
          : ['default']
      },
      optimizeDeps: {
        include: ['@/components/CmkIcon/icons.constants']
      },
      server: {
        strictPort: true,
        fs: {
          allow: ['.', '../cmk-frontend/']
        },
        proxy: {
          // dev server proxies whole checkmk to inject js resources and support auto hot reloading
          '^(?!/cmk-frontend-vue-ahr)': 'http://localhost/'
        }
      },
      base: '/cmk-frontend-vue-ahr'
    }
  }
})
