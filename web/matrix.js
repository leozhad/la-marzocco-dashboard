export function createMatrix(canvas, button) {
  const ctx = canvas.getContext('2d');
  const reduced = matchMedia('(prefers-reduced-motion:reduce)');
  let enabled = false, frame = 0, columns = [], width = 0, height = 0, last = 0;
  let draws = 0;
  try { enabled = localStorage.getItem('espresso.matrix') === 'true'; } catch {}
  const glyphs = '0123456789∴:·☕';
  function paint(still = false) {
    if (!ctx) return;
    ctx.clearRect(0, 0, width, height);
    ctx.font = '12px ui-monospace, monospace';
    for (const column of columns) {
      if (!still) {
        column.y += column.speed;
        if (column.y - column.length * 18 > height) column.y = -Math.random() * height * .3;
      }
      for (let j = 0; j < column.length; j++) {
        const y = column.y - j * 18;
        if (y < 0 || y > height) continue;
        const alpha = (1 - j / column.length) * (still ? .17 : .32);
        ctx.fillStyle = j === 0 ? `rgba(223,181,128,${alpha})` : `rgba(118,163,136,${alpha})`;
        ctx.fillText(column.chars[j], column.x, y);
      }
    }
    draws++;
  }
  function loop(time) {
    frame = 0;
    if (!enabled || document.hidden || reduced.matches) return;
    if (time - last >= 45) { paint(); last = time; }
    frame = requestAnimationFrame(loop);
  }
  function resize() {
    width = innerWidth; height = innerHeight;
    const ratio = Math.min(devicePixelRatio, 1.5);
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    canvas.style.width = `${width}px`;canvas.style.height = `${height}px`;
    if (!ctx) return;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    columns = Array.from({length:Math.ceil(width/33)},(_,i)=>{
      const length=10+Math.floor(Math.random()*13);
      return {x:i*33+12,y:Math.random()*height,speed:.65+Math.random()*1.6,length,
        chars:Array.from({length},()=>glyphs[Math.floor(Math.random()*glyphs.length)])};
    });
    if(enabled)paint(true);
  }
  function sync() {
    if(frame)cancelAnimationFrame(frame);frame=0;
    canvas.hidden=!enabled;
    document.body.classList.toggle('matrix-enabled',enabled);
    button.setAttribute('aria-pressed',String(enabled));
    button.querySelector('.matrix-state').textContent=enabled?'On':'Off';
    if(enabled&&!document.hidden) {
      if(reduced.matches)paint(true);else frame=requestAnimationFrame(loop);
    }
  }
  button.addEventListener('click',()=>{
    enabled=!enabled;
    try {localStorage.setItem('espresso.matrix',String(enabled));}catch {}
    sync();
  });
  window.addEventListener('resize',()=>{resize();sync();});
  document.addEventListener('visibilitychange',sync);
  reduced.addEventListener('change',sync);
  resize();sync();
  return {diagnostics:()=>({enabled,reducedMotion:reduced.matches,animating:!!frame,draws,columns:columns.length})};
}
