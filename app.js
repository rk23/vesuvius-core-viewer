import { mountViewer } from './viewer.js';

const $ = id => document.getElementById(id);
const expected = ['schema_version', 'title', 'voxel_mm', 'step_vx', 'origin', 'centre', 'z_range',
  'radius_mm', 'axis', 'axis_ok', 'points_b64', 'points_total', 'feature_text', 'slices', 'envelope',
  'slice_um', 'provenance'];
let dispose = null, generation = 0;

export function validateScene(d) {
  const exact = (object, fields) => object && typeof object === 'object' && !Array.isArray(object) &&
    Object.keys(object).length === fields.length && fields.every(field => Object.hasOwn(object, field));
  const number = x => typeof x === 'number' && Number.isFinite(x);
  const vector = (x, n) => Array.isArray(x) && x.length === n && x.every(number);
  if (!exact(d, expected) || d.schema_version !== 1) throw new Error('Unsupported scene format.');
  if (!['title', 'feature_text', 'points_b64'].every(k => typeof d[k] === 'string') ||
      !['voxel_mm', 'step_vx', 'radius_mm', 'slice_um'].every(k => number(d[k]) && d[k] > 0) ||
      !vector(d.origin, 3) || !vector(d.centre, 3) || !vector(d.z_range, 2) || d.z_range[1] <= d.z_range[0] ||
      !Array.isArray(d.axis) || d.axis.length < 2 || !d.axis.every(x => vector(x, 3)) ||
      !d.axis.every((x, i) => !i || x[0] > d.axis[i - 1][0]) ||
      (d.axis_ok !== null && (!vector(d.axis_ok, 2) || d.axis_ok[1] < d.axis_ok[0]))) {
    throw new Error('Invalid coordinates or dimensions in scene.');
  }
  const points = atob(d.points_b64);
  if (points.length % 6 || !Number.isInteger(d.points_total) || d.points_total < points.length / 6) {
    throw new Error('Invalid point buffer.');
  }
  if (!Array.isArray(d.slices) || !d.slices.every((s, i) =>
    exact(s, ['z', 'cx', 'cy', 'half_vx', 'jpg']) && ['z', 'cx', 'cy', 'half_vx'].every(k => number(s[k])) &&
    s.half_vx > 0 && s.z >= d.z_range[0] && s.z < d.z_range[1] && (!i || s.z > d.slices[i - 1].z) &&
    typeof s.jpg === 'string' && s.jpg.startsWith('/9j/'))) throw new Error('Invalid CT slices.');
  if (!Array.isArray(d.envelope) || !d.envelope.every(e => exact(e, ['z', 'xy']) && number(e.z) &&
    e.z >= d.z_range[0] && e.z < d.z_range[1] && Array.isArray(e.xy) && e.xy.length >= 6 &&
    e.xy.length % 2 === 0 && e.xy.every(number))) throw new Error('Invalid outlines.');
  if (!exact(d.provenance, ['volume_url', 'data_license', 'data_attribution', 'data_reference',
    'axis_source', 'axis_license', 'axis_note', 'display']) ||
    !Object.values(d.provenance).every(x => typeof x === 'string')) throw new Error('Invalid provenance.');
  for (const field of ['volume_url', 'data_reference']) {
    if (!d.provenance[field]) continue;
    const url = new URL(d.provenance[field]);
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.search) {
      throw new Error('Source links must be public HTTP(S) URLs without credentials or query strings.');
    }
  }
  return d;
}

async function decode(bytes) {
  let blob = new Blob([bytes]);
  const header = new Uint8Array(bytes, 0, Math.min(2, bytes.byteLength));
  if (header[0] === 0x1f && header[1] === 0x8b) {
    if (typeof DecompressionStream === 'undefined') throw new Error('This browser needs gzip decompression support.');
    blob = await new Response(blob.stream().pipeThrough(new DecompressionStream('gzip'))).blob();
  }
  if (blob.size > 128 * 1024 * 1024) throw new Error('Scene exceeds the 128 MiB uncompressed size limit.');
  return validateScene(JSON.parse(await blob.text()));
}

async function load(read) {
  const current = ++generation;
  document.body.dataset.ready = 'loading';
  $('loading').hidden = false; $('loading').textContent = 'Loading scene…';
  try {
    const data = await decode(await read());
    if (current !== generation) return;
    if (dispose) dispose();
    dispose = mountViewer(data);
    $('volumeLink').hidden = !data.provenance.volume_url;
    $('loading').hidden = true;
    document.body.dataset.ready = 'true';
  } catch (error) {
    if (current !== generation) return;
    $('loading').textContent = `Could not load scene: ${error.message}`;
    document.body.dataset.ready = 'error';
  }
}

function readURL(path) {
  const url = new URL(path, location.href);
  if (url.origin !== location.origin) throw new Error('Scene files must be served from this site.');
  return async () => {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status} for scene file`);
    return response.arrayBuffer();
  };
}

$('sceneFile').addEventListener('change', event => {
  const file = event.target.files[0];
  if (file) load(() => file.arrayBuffer());
});

try {
  const response = await fetch('data/catalog.json');
  if (!response.ok) throw new Error(`HTTP ${response.status} for scene catalog`);
  const catalog = await response.json();
  const select = $('sceneSelect');
  catalog.scenes.forEach(s => {
    const option = document.createElement('option'); option.value = s.id; option.textContent = s.title;
    select.appendChild(option);
  });
  const query = new URLSearchParams(location.search);
  const initial = catalog.scenes.find(s => s.id === query.get('scene')) || catalog.scenes[0];
  select.value = initial.id;
  select.addEventListener('change', () => {
    const entry = catalog.scenes.find(s => s.id === select.value);
    history.replaceState(null, '', `?scene=${encodeURIComponent(entry.id)}`);
    $('sceneFile').value = '';
    load(readURL(entry.scene));
  });
  await load(readURL(query.get('file') || initial.scene));
} catch (error) {
  $('loading').hidden = false; $('loading').textContent = `${error.message}. You can still open a scene file.`;
  document.body.dataset.ready = 'error';
}
