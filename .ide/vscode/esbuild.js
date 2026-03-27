const esbuild = require('esbuild')
const watch = process.argv.includes('--watch')

async function main() {
  const ctx = await esbuild.context({
    entryPoints: ['src/extension.ts'],
    bundle: true,
    outfile: 'out/extension.js',
    external: ['vscode'],
    format: 'cjs',
    platform: 'node',
    target: 'node18',
    sourcemap: true,
    loader: { '.css': 'text' }
  })

  if (watch) {
    await ctx.watch()
    console.log('Watching for changes...')
  } else {
    await ctx.rebuild()
    await ctx.dispose()
    console.log('Build complete.')
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
