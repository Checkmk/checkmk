import { default as eslint, default as js } from '@eslint/js'
import skipFormatting from '@vue/eslint-config-prettier/skip-formatting'
import vueTsEslintConfig from '@vue/eslint-config-typescript'
import pluginVue from 'eslint-plugin-vue'
import fs from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'
import tseslint from 'typescript-eslint'

async function loadOptionalPackageConfigs() {
  const packagesDir = path.resolve('packages')
  if (!fs.existsSync(packagesDir)) {
    return []
  }

  const loadedConfigs = []

  for (const entry of fs.readdirSync(packagesDir, { withFileTypes: true })) {
    if (!entry.isDirectory()) {
      continue
    }

    const configPath = path.join(packagesDir, entry.name, 'eslint.config.mjs')
    if (!fs.existsSync(configPath)) {
      continue
    }

    const imported = await import(pathToFileURL(configPath).href)
    const config = imported.default ?? imported

    if (Array.isArray(config)) {
      loadedConfigs.push(...config)
    } else if (config) {
      loadedConfigs.push(config)
    }
  }

  return loadedConfigs
}

const optionalPackageConfigs = await loadOptionalPackageConfigs()

export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue,js,jsx,cjs,mjs,cts}']
  },

  {
    name: 'app/files-to-ignore',
    ignores: [
      '**/*.config.{js,cjs}',
      '**/vite.config.*',
      '**/dist/**',
      '**/dist-dev/**',
      '**/dist-ssr/**',
      '**/coverage/**',
      'packages/cmk-frontend-vue/ui-component-library/public/mockServiceWorker.js',
      '.stylelintrc.js',
      'packages/cmk-frontend-vue/scripts/stylelint-vue-bem-naming-convention.js'
    ]
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  ...vueTsEslintConfig(),
  skipFormatting,
  ...optionalPackageConfigs
]
