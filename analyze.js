const { execSync } = require('child_process');
const fs = require('fs');

// Get the latest snapshot
execSync('playwright-cli snapshot --filename=gen_snap.yaml', { cwd: 'e:/咕咕嘎嘎' });

// Read snapshot
const snap = fs.readFileSync('e:/咕咕嘎嘎/gen_snap.yaml', 'utf8');

// Find all button refs
const btnRefs = snap.match(/button[^\n]*\[ref=e(\d+)\]/g) || [];
console.log('Buttons found:');
btnRefs.forEach(b => console.log('  ' + b));

// Try clicking each button ref to find the generate button
const refs = [...new Set(btnRefs.map(b => b.match(/ref=e(\d+)/)[1]))];
console.log('Refs:', refs);
