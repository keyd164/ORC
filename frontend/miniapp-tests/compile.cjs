const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { wxmlToJs, wxssToJs } = require('miniprogram-compiler');
const root = path.resolve(__dirname, '../miniapp');
const config = JSON.parse(fs.readFileSync(path.join(root, 'app.json'), 'utf8'));
for (const page of config.pages) {
  for (const ext of ['js', 'json', 'wxml']) {
    if (!fs.existsSync(path.join(root, page + '.' + ext))) throw Error('Missing ' + page + '.' + ext);
  }
  new vm.Script(fs.readFileSync(path.join(root, page + '.js'), 'utf8'), { filename: page });
  JSON.parse(fs.readFileSync(path.join(root, page + '.json'), 'utf8'));
}
new vm.Script('(function(global){' + wxmlToJs(root, { maxBuffer: 8 * 1024 * 1024 }) + '})');
new vm.Script('(function(global){' + wxssToJs(root, { maxBuffer: 8 * 1024 * 1024 }) + '})');
console.log('WXML/WXSS compiled; scripts and configuration checked for ' + config.pages.length + ' pages.');
