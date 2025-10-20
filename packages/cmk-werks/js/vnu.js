'use strict'

const { spawn } = require('child_process')
const vnu = require('vnu-jar')

const p = spawn('java', ['-jar', vnu].concat(process.argv.slice(2)), {
  stdio: 'inherit'
})

p.on('exit', (code) => {
  process.exit(code)
})
