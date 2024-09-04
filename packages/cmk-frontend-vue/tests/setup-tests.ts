import { mixinUniqueId } from '@/plugins'
import { config } from '@vue/test-utils'
import failOnConsole from 'vitest-fail-on-console'
import '@testing-library/jest-dom/vitest'

failOnConsole({
  shouldFailOnAssert: true,
  shouldFailOnDebug: true,
  shouldFailOnInfo: true,
  shouldFailOnLog: true
})

config.global.plugins = [mixinUniqueId]
