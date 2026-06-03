// Find and click the generate/send button on jimeng video creation page
const allBtns = document.querySelectorAll('button:not([disabled])');
let candidates = [];

for (const btn of allBtns) {
  const html = btn.innerHTML?.substring(0, 200);
  const text = btn.textContent?.trim()?.substring(0, 100);
  const cls = btn.className;
  const rect = btn.getBoundingClientRect();
  const hasSvg = btn.querySelector('svg') !== null;
  
  // Only consider visible buttons
  if (rect.width === 0 || rect.height === 0) continue;
  
  candidates.push({
    text,
    cls: cls?.substring(0, 50),
    hasSvg,
    html: html?.substring(0, 100),
    x: Math.round(rect.x + rect.width/2),
    y: Math.round(rect.y + rect.height/2),
    w: Math.round(rect.width),
    h: Math.round(rect.height),
    nearBottom: rect.y > 300
  });
}

// Try to find the generate button: it's usually near the input area, has a send icon
// Sort candidates by position - the send button is usually at the bottom-right of the input area
const result = candidates.map((c, i) => ({...c, index: i}));
console.log(JSON.stringify(result, null, 2));

// Try to click the most likely candidate (lv-btn-primary at the bottom of input area)
const target = candidates.find((c, i) => 
  c.cls?.includes('lv-btn-primary') && c.h > 20 && c.h < 50 && c.y > 250 && c.y < 500
);

if (target) {
  const targetBtn = [...allBtns].find((b, i) => {
    const r = b.getBoundingClientRect();
    return Math.abs(r.x + r.width/2 - target.x) < 5 && Math.abs(r.y + r.height/2 - target.y) < 5;
  });
  if (targetBtn) {
    targetBtn.click();
    return 'clicked generate button at ' + target.x + ',' + target.y;
  }
}

return 'no target found. candidates: ' + JSON.stringify(result);
