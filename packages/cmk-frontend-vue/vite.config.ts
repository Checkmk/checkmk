/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import { type RollupLog } from 'rollup'
import { type UserConfig, defineConfig } from 'vite'
import VueDevTools from 'vite-plugin-vue-devtools'

// https://vitejs.dev/config/
export default defineConfig(({ command }) => {
  const resultBuild: UserConfig = {
    clearScreen: false,
    plugins: [
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
        VueDevTools({
          componentInspector: true,
          appendTo: /main\.ts$/
        })
      ],
      test: {
        // enable jest-like global test APIs
        globals: true,
        environment: 'jsdom',
        setupFiles: ['tests/setup-tests.ts']
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
