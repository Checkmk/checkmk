import { mixinUniqueId } from '@/plugins'
import { config } from '@vue/test-utils'

config.global.plugins = [mixinUniqueId]
