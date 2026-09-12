import { createMatrix } from './matrix.js';

let data = JSON.parse(document.getElementById('machine-data').textContent);
let selectedTime = data.recent_shots?.[0]?.time;
let selectedComponent = 'boiler';
let model = null;
let refreshFailed = false;
let refreshing = false;
const matrix = createMatrix(document.getElementById('matrix-canvas'), document.getElementById('matrix-toggle'));
const set = (selector, text) => document.querySelectorAll(selector).forEach(element => { element.textContent = text; });
const number = value => Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '—';
const dateFormat = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
const timeFormat = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit', timeZoneName: 'short' });
const date = value => value && Number.isFinite(new Date(value).getTime()) ? dateFormat.format(new Date(value)) : 'Not reported';
const tabs = [...document.querySelectorAll('[data-tab]')];

function showTab(name) {
  if (!tabs.some(button => button.dataset.tab === name)) name = 'overview';
  tabs.forEach(button => {
    const active = button.dataset.tab === name;
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll('.panel').forEach(panel => { panel.hidden = panel.id !== name; });
  model?.resize();
  window.scrollTo({ top: 0, behavior: 'instant' });
}
tabs.forEach((button, index) => {
  button.addEventListener('click', () => showTab(button.dataset.tab));
  button.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 :
      (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    showTab(tabs[next].dataset.tab); tabs[next].focus();
  });
});
document.querySelectorAll('[data-open]').forEach(button => button.addEventListener('click', () => {
  showTab(button.dataset.open); document.getElementById(`tab-${button.dataset.open}`).focus();
}));
document.getElementById('open-cutaway').addEventListener('click', () => { showTab('overview'); model?.mode('cutaway'); });
document.getElementById('flow-toggle').addEventListener('click', event => {
  const active = event.currentTarget.getAttribute('aria-pressed') !== 'true';
  event.currentTarget.setAttribute('aria-pressed', String(active));
  event.currentTarget.textContent = active ? 'Pause the illustration' : 'Trace the water paths';
  document.querySelector('.circuit').classList.toggle('flowing', active);
});

function component(name) {
  selectedComponent = name;
  const status = data.status || {}, brew = data.brewing || {};
  const descriptions = {
    boiler: ['01 / Integrated brew group',
      `Target ${number(status.coffee_boiler_temp)}°F · ${status.coffee_boiler_ready ? 'Ready' : 'Not ready'}. The V1.5 parts catalog specifies a 0.17 L integrated brew boiler and a separate 3 L steam boiler.`],
    group: ['02 / Brew-by-weight',
      `Dose A: ${number(brew.dose_1)}g · Dose B: ${number(brew.dose_2)}g · ${brew.dose_mode || 'Mode not reported'}. These are beverage yield presets, not dry coffee dose.`],
    scale: ['03 / La Marzocco Connected Scale',
      `Made with Acaia · ${status.scale_connected ? 'Connected' : 'Disconnected'} · ${number(status.scale_battery)}% battery. ${status.scale_calibration_required ? 'Calibration required.' : 'No calibration requested.'} Completed-shot weights appear in the brew log.`],
  };
  document.querySelectorAll('[data-component]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.component === name)));
  set('#component-title', descriptions[name][0]); set('#component-description', descriptions[name][1]);
}
document.querySelectorAll('[data-component]').forEach(button => button.addEventListener('click', () => component(button.dataset.component)));

function freshness() {
  const age = Date.now() - new Date(data.timestamp).getTime();
  const stale = !Number.isFinite(age) || age > 10 * 60 * 1000;
  const minutes = Math.max(0, Math.floor(age / 60000));
  set('#freshness-label', refreshFailed ? 'Refresh unavailable' : stale ? 'Data delayed' :
    minutes < 1 ? 'Updated just now' : `Updated ${minutes} min ago`);
  set('#snapshot-time', Number.isFinite(age) ? timeFormat.format(new Date(data.timestamp)) : 'Last update not reported');
  document.getElementById('freshness-dot').classList.toggle('stale', stale || refreshFailed);
  document.querySelector('.freshness').title = `Last successful collection: ${date(data.timestamp)}`;
  const status = data.status || {};
  set('#machine-state', stale ? 'DATA DELAYED' : !status.power_on ? 'MACHINE OFF' :
    status.coffee_boiler_ready ? 'READY TO BREW' : 'WARMING UP');
}

function selectedShot(index) {
  const shots = data.recent_shots || [];
  const shot = shots[index];
  if (!shot) {
    set('.duration', '—'); set('.yield', '—'); set('.target', '—');
    set('.shot-date', 'No recent shots reported'); set('.shot-dose', '');
    set('#comparison', 'Comparison will appear when recent shots are available.');
    set('#latest-title', 'Recent shots'); set('#journal-title', 'Recent shots');
    return;
  }
  selectedTime = shot.time;
  set('.duration', number(shot.extraction_seconds)); set('.yield', number(shot.dose_value));
  set('.target', number(shot.target_temperature_f)); set('.shot-date', date(shot.time));
  set('.shot-dose', shot.dose_index === 'DoseA' ? 'Dose A' : shot.dose_index === 'DoseB' ? 'Dose B' : shot.dose_index || '');
  set('#latest-title', index === 0 ? 'The latest shot' : `Shot ${index + 1}`);
  set('#journal-title', index === 0 ? 'The latest shot' : `Shot ${index + 1}`);
  document.querySelectorAll('[data-shot]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.shot) === index)));
  document.querySelectorAll('[data-row]').forEach(row => row.classList.toggle('selected', Number(row.dataset.row) === index));
  const average = shots.reduce((sum, item) => sum + item.extraction_seconds, 0) / shots.length;
  const meanYield = shots.reduce((sum, item) => sum + item.dose_value, 0) / shots.length;
  set('#comparison', `${shots.length}-shot average: ${average.toFixed(1)}s and ${meanYield.toFixed(1)}g. This shot ran ${Math.abs(shot.extraction_seconds - average).toFixed(1)}s ${shot.extraction_seconds >= average ? 'longer' : 'shorter'} than that average.`);
}
function renderShots() {
  const miniature = document.querySelector('.mini-shots'), body = document.querySelector('.journal-list tbody');
  miniature.replaceChildren(); body.replaceChildren();
  const shots = data.recent_shots || [];
  shots.forEach((shot, index) => {
    const button = document.createElement('button');
    button.textContent = index === 0 ? 'Latest' : `Shot ${index + 1}`;
    button.dataset.shot = index; button.setAttribute('aria-pressed', 'false');
    button.addEventListener('click', () => selectedShot(index)); miniature.append(button);
    const row = document.createElement('tr'); row.dataset.row = index;
    const cell = document.createElement('td'), control = document.createElement('button'), time = document.createElement('small');
    control.append(document.createTextNode(index === 0 ? 'Latest' : `Shot ${index + 1}`));
    time.textContent = date(shot.time); control.append(time);
    control.addEventListener('click', () => {
      selectedShot(index);
      if (innerWidth <= 700) document.querySelector('.journal-layout>aside').scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    cell.append(control); row.append(cell);
    [`${number(shot.extraction_seconds)}s`, `${number(shot.dose_value)}g`, `${number(shot.target_temperature_f)}°F`].forEach(text => {
      const td = document.createElement('td'); td.textContent = text; row.append(td);
    });
    body.append(row);
  });
  const index = shots.findIndex(shot => shot.time === selectedTime);
  selectedShot(index < 0 ? 0 : index);
}
function renderTrend() {
  const trend = data.usage_trend;
  const barsRoot = document.querySelector('.week-bars');
  barsRoot.replaceChildren();
  set('#week-shots', number(trend?.total_shots)); set('#week-flushes', number(trend?.total_flushes));
  set('.day-readout', trend ? `Select a day · ${trend.timezone}` : 'Daily activity is not currently reported.');
  if (!trend) return;
  const max = Math.max(...trend.daily.flatMap(day => [day.shots, day.flushes]), 1);
  trend.daily.forEach(day => {
    const button = document.createElement('button'); button.className = 'day';
    button.setAttribute('aria-label', `${day.label}: ${day.shots} shots, ${day.flushes} flushes`);
    const bars = document.createElement('span'); bars.className = 'bars';
    ['shots', 'flushes'].forEach((key, index) => {
      const bar = document.createElement('span'); bar.className = `bar${index ? ' flush' : ''}`;
      bar.style.height = `${day[key] / max * 74}px`; if (day[key] === 0) bar.style.visibility = 'hidden';
      bars.append(bar);
    });
    const label = document.createElement('small'); label.textContent = day.label.split(' ')[0];
    button.append(bars, label);
    const describe = () => set('.day-readout', `${day.label} · ${day.shots} shots · ${day.flushes} flushes`);
    button.addEventListener('click', describe); button.addEventListener('focus', describe);
    barsRoot.append(button);
  });
}
function renderDetails() {
  const settings = data.settings || {}, care = data.maintenance || {}, status = data.status || {};
  set('#lifetime', `${number(data.statistics?.total_shots)} shots\n${number(data.statistics?.total_flushes)} flushes`);
  set('#maintenance', `Last cleaning: ${care.last_cleaning_date || 'Not reported'}\nSmart standby: ${settings.smart_standby_enabled ? `${settings.smart_standby_minutes} minutes` : 'Disabled'}\nWater: ${settings.plumbed_in ? 'Plumbed in' : 'Tank'}`);
  set('#network-details', `Wi-Fi: ${settings.wifi_ssid || 'Not reported'} (${number(settings.wifi_signal)} dBm)\nScale: ${status.scale_name || 'Not reported'}\nCalibration: ${status.scale_calibration_required ? 'Required' : 'Not requested'}\nClient: pylamarzocco ${data.client_version || ''}`);
  set('#firmware', `${data.machine_info?.firmware_version || 'Not reported'}\nUpdates: ${care.firmware_update_available ? 'Available' : 'Up to date'}`);
  const notes = document.getElementById('firmware-notes');
  const opened = new Set([...notes.querySelectorAll('details[open]')].map(el => el.dataset.name));
  notes.replaceChildren();
  for (const firmware of care.firmware_notes || []) {
    const details = document.createElement('details'), summary = document.createElement('summary'), content = document.createElement('p');
    details.dataset.name = firmware.name; details.open = opened.has(firmware.name);
    summary.textContent = `${firmware.name} ${firmware.version} release notes`; content.textContent = firmware.notes;
    details.append(summary, content); notes.append(details);
  }
}
function render() {
  const status = data.status || {};
  set('#boiler-value', number(status.coffee_boiler_temp));
  set('#boiler-status', status.coffee_boiler_ready ? 'Ready' : 'Not ready');
  set('#steam-value', status.steam_boiler_status || '—');
  set('#battery-value', Number.isFinite(status.scale_battery) ? Math.round(status.scale_battery) : '—');
  set('#scale-state', status.scale_connected ? 'Connected Scale' : 'Disconnected');
  renderShots(); renderTrend(); renderDetails(); component(selectedComponent); freshness(); model?.update(data);
}
async function refresh() {
  if (refreshing) return;
  refreshing = true;
  const button = document.getElementById('refresh-data'); button.disabled = true;
  try {
    const response = await fetch('/data.json', { cache: 'no-store', signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const next = await response.json();
    if (!next.status || !next.statistics || !Number.isFinite(new Date(next.timestamp).getTime())) throw new Error('Invalid machine data');
    refreshFailed = false;
    if (next.timestamp !== data.timestamp) { data = next; render(); }
    freshness();
  } catch (error) {
    refreshFailed = true; freshness();
    console.warn('Keeping the last successful machine data:', error.message);
  } finally { refreshing = false; button.disabled = false; }
}
document.getElementById('refresh-data').addEventListener('click', refresh);
document.addEventListener('visibilitychange', () => { if (!document.hidden) { freshness(); refresh(); } });
setInterval(() => { if (!document.hidden) refresh(); }, 60000);
setInterval(() => { if (!document.hidden) freshness(); }, 15000);
render();
import('./machine.js').then(({createMachine}) => {
  model = createMachine(document.getElementById('machine-viewport'), component); model.update(data);
}).catch(error => {
  console.warn('3D view unavailable:', error.message);
  set('#model-loading', '3D is unavailable in this browser. Your machine readings and brew log are still available.');
  document.querySelectorAll('[data-mode],[data-camera],#rotate-model,#interact-model').forEach(button => { button.disabled = true; });
  document.querySelectorAll('.hotspot').forEach(button => { button.hidden = true; });
});
window.espressoDiagnostics = () => ({
  dataTimestamp: data.timestamp, clientVersion: data.client_version, refreshing, refreshFailed,
  selectedShot: selectedTime, shotCount: data.recent_shots?.length || 0,
  model: model?.diagnostics() || null, matrix: matrix.diagnostics(),
});
