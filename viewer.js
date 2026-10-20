import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export function mountViewer(D) {
const abort = new AbortController(), { signal } = abort;
const $ = id => document.getElementById(id);
const VX = D.voxel_mm, C = D.centre;
$('title').textContent = D.title; document.title = D.title;
$('about').textContent = `Points: ${D.feature_text}, within ${D.radius_mm} mm of the axis; z ${D.z_range[0]}–${D.z_range[1]}. ` +
  (D.axis_ok ? `Axis reference range: z ${D.axis_ok[0]}–${D.axis_ok[1]}. ` : '') +
  'Axes: x red, y green, z blue (z drawn downward). Drag to rotate, right-drag to pan, scroll to zoom.';
$('attribution').textContent = `${D.provenance.data_attribution} · ${D.provenance.data_license}`;
$('axisNote').textContent = D.provenance.axis_note;
$('volumeLink').href = D.provenance.volume_url;
const W = (x, y, z) => new THREE.Vector3((x - C[0]) * VX, (y - C[1]) * VX, (z - C[2]) * VX);
function buf(b64) { const s = atob(b64), u = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i); return u.buffer; }
const tr = D.axis;
function axisAt(z) {
  if (z <= tr[0][0]) return [tr[0][1], tr[0][2]];
  for (let i = 1; i < tr.length; i++) if (z <= tr[i][0]) {
    const a = tr[i - 1], b = tr[i], f = (z - a[0]) / (b[0] - a[0]);
    return [a[1] + f * (b[1] - a[1]), a[2] + f * (b[2] - a[2])]; }
  const l = tr[tr.length - 1]; return [l[1], l[2]];
}
const view = $('view');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
view.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x0e1116);
const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 5000);
camera.up.set(0, 0, -1);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.AxesHelper(4));

// feature points
const g = new Int16Array(buf(D.points_b64)), n = g.length / 3;
const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), rr = new Float32Array(n), th = new Float32Array(n), zz = new Float32Array(n);
for (let i = 0; i < n; i++) {
  const x = D.origin[0] + D.step_vx * g[3 * i], y = D.origin[1] + D.step_vx * g[3 * i + 1], z = D.origin[2] + D.step_vx * g[3 * i + 2];
  const v = W(x, y, z); pos[3 * i] = v.x; pos[3 * i + 1] = v.y; pos[3 * i + 2] = v.z;
  const t = axisAt(z); rr[i] = Math.hypot(x - t[0], y - t[1]) * VX;
  th[i] = (Math.atan2(y - t[1], x - t[0]) * 180 / Math.PI + 360) % 360; zz[i] = z;
}
const geo = new THREE.BufferGeometry();
geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
geo.setAttribute('rmm', new THREE.BufferAttribute(rr, 1));
const mat = new THREE.ShaderMaterial({
  uniforms: { size: { value: 1.6 }, scale: { value: 400 }, zMin: { value: -1e9 }, zMax: { value: 1e9 }, rMax: { value: 99 } },
  vertexShader: `attribute vec3 color; attribute float rmm; varying vec3 vC; varying float vK;
    uniform float size, scale, zMin, zMax, rMax;
    void main() { vC = color; vK = (position.z < zMin || position.z > zMax || rmm > rMax) ? 0.0 : 1.0;
      vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv;
      gl_PointSize = vK * clamp(size * scale * 0.1 / max(-mv.z, 0.1), 1.0, 32.0); }`,
  fragmentShader: `varying vec3 vC; varying float vK;
    void main() { if (vK < 0.5) discard; vec2 d = gl_PointCoord - 0.5; if (dot(d, d) > 0.25) discard; gl_FragColor = vec4(vC, 1.0); }`,
});
const points = new THREE.Points(geo, mat); scene.add(points);
function recolour(mode) {
  const c = new THREE.Color();
  for (let i = 0; i < n; i++) {
    if (mode === 'angle') c.setHSL(th[i] / 360, 0.9, 0.55);
    else if (mode === 'z') c.setHSL(0.7 * (zz[i] - D.z_range[0]) / (D.z_range[1] - D.z_range[0]), 0.85, 0.55);
    else c.setHSL(0.75 * Math.min(rr[i] / D.radius_mm, 1), 0.85, 0.55);
    col[3 * i] = c.r; col[3 * i + 1] = c.g; col[3 * i + 2] = c.b;
  }
  geo.attributes.color.needsUpdate = true;
}
recolour('angle');

// Outer cross-section outlines.
const env = new THREE.Group(), envMat = new THREE.LineBasicMaterial({ color: 0x8794a3, transparent: true, opacity: 0.35, depthWrite: false });
(D.envelope || []).forEach(L => {
  const pts = []; for (let i = 0; i < L.xy.length; i += 2) pts.push(W(L.xy[i], L.xy[i + 1], L.z));
  const loop = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts), envMat); loop.userData.z = L.z; env.add(loop);
});
scene.add(env);
$('outline').hidden = !D.envelope.length;


// axis
const axisLine = new THREE.Line(new THREE.BufferGeometry().setFromPoints(tr.map(t => W(t[1], t[2], t[0]))),
  new THREE.LineBasicMaterial({ color: 0xffffff }));
scene.add(axisLine);

// CT slices
const S = D.slices, tex = new Array(S.length);
const plane = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false }));
scene.add(plane);
function getTex(i) {
  if (!tex[i]) { const img = new Image(); const t = new THREE.Texture(img); t.flipY = false; t.colorSpace = THREE.SRGBColorSpace;
    img.onload = () => { t.needsUpdate = true; }; img.src = 'data:image/jpeg;base64,' + S[i].jpg; tex[i] = t; }
  return tex[i];
}
const nearestSlice = z => { let b = 0; S.forEach((s, i) => { if (Math.abs(s.z - z) < Math.abs(S[b].z - z)) b = i; }); return b; };
let cur = 0;
$('sOn').checked = true; $('sClip').checked = false; $('gOn').checked = true; $('gCol').value = 'angle';
$('tOn').checked = true; $('envOn').checked = true;
const sZ = $('sZ'); sZ.min = 0; sZ.max = Math.max(S.length - 1, 0); sZ.step = 1;
function setSlice(i) {
  if (!S.length) return;
  cur = i; sZ.value = i; const s = S[i], size = 2 * s.half_vx * VX;
  plane.material.map = getTex(i); plane.material.needsUpdate = true;
  plane.scale.set(size, size, 1); plane.position.copy(W(s.cx, s.cy, s.z));
  $('sZV').textContent = s.z; applyClip();
}
function applyClip() {
  const zmin = (+$('zMin').value - C[2]) * VX, zmax = (+$('zMax').value - C[2]) * VX;
  const clip = $('sClip').checked && S.length;
  mat.uniforms.zMin.value = clip ? Math.max(zmin, (S[cur].z - C[2]) * VX) : zmin; mat.uniforms.zMax.value = zmax;
}

// controls
for (const [id, v] of [['zMin', D.z_range[0]], ['zMax', D.z_range[1]]]) {
  const e = $(id); e.min = D.z_range[0]; e.max = D.z_range[1]; e.step = Math.min(10, D.z_range[1] - D.z_range[0]); e.value = v;
}
$('rMax').min = Math.min(0.1, D.radius_mm); $('rMax').max = D.radius_mm; $('rMax').value = D.radius_mm;
function sync() {
  $('zMinV').textContent = $('zMin').value; $('zMaxV').textContent = $('zMax').value;
  $('rMaxV').textContent = (+$('rMax').value).toFixed(1) + ' mm'; $('pSizeV').textContent = (+$('pSize').value).toFixed(1);
  $('sOpV').textContent = (+$('sOp').value).toFixed(2);
  mat.uniforms.rMax.value = +$('rMax').value; mat.uniforms.size.value = +$('pSize').value;
  plane.material.opacity = +$('sOp').value; points.visible = $('gOn').checked; plane.visible = $('sOn').checked && S.length > 0;
  axisLine.visible = $('tOn').checked; applyClip();
  envMat.opacity = +$('envOp').value; $('envOpV').textContent = (+$('envOp').value).toFixed(2);
  env.visible = $('envOn').checked;
  env.children.forEach(l => { l.visible = l.userData.z >= +$('zMin').value && l.userData.z <= +$('zMax').value; });
}
document.querySelectorAll('#panel input').forEach(e => e.addEventListener('input', sync, { signal }));
sZ.addEventListener('input', () => setSlice(+sZ.value), { signal });
$('gCol').addEventListener('change', e => recolour(e.target.value), { signal });
// Frame the central CT region at the actual viewport aspect ratio.
const bounds = new THREE.Box3();
tr.forEach(t => bounds.expandByPoint(W(t[1], t[2], t[0])));
if (n) { geo.computeBoundingBox(); bounds.union(geo.boundingBox); }
S.forEach(s => {
  bounds.expandByPoint(W(s.cx - s.half_vx, s.cy - s.half_vx, s.z));
  bounds.expandByPoint(W(s.cx + s.half_vx, s.cy + s.half_vx, s.z));
});
const corners = [];
for (const x of [bounds.min.x, bounds.max.x]) for (const y of [bounds.min.y, bounds.max.y])
  for (const z of [bounds.min.z, bounds.max.z]) corners.push(new THREE.Vector3(x, y, z));
controls.target.copy(bounds.getCenter(new THREE.Vector3()));
function look(direction) {
  direction.normalize();
  const right = new THREE.Vector3().crossVectors(camera.up, direction);
  if (right.lengthSq() < 1e-10) right.set(1, 0, 0);
  right.normalize();
  const up = new THREE.Vector3().crossVectors(direction, right).normalize();
  const tanV = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2), tanH = tanV * camera.aspect;
  let distance = 1;
  corners.forEach(corner => {
    const offset = corner.clone().sub(controls.target);
    distance = Math.max(distance, offset.dot(direction) + 1.1 *
      Math.max(Math.abs(offset.dot(right)) / tanH, Math.abs(offset.dot(up)) / tanV));
  });
  camera.far = Math.max(5000, distance * 4); camera.updateProjectionMatrix();
  camera.position.copy(controls.target).addScaledVector(direction, distance); controls.update();
}
$('vTop').onclick = () => look(new THREE.Vector3(0, 0.0001, -1));
$('vFront').onclick = () => look(new THREE.Vector3(0, 1, 0));
$('vSide').onclick = () => look(new THREE.Vector3(-1, 0, 0));
$('vFit').onclick = () => look(camera.position.clone().sub(controls.target));
$('vFocus').onclick = () => { controls.target.copy(plane.position); controls.update(); };
$('stats').textContent = `${n.toLocaleString()} of ${D.points_total.toLocaleString()} feature voxels shown; ${S.length} CT slices (${Math.round(D.slice_um)} µm).`;
setSlice(nearestSlice(C[2])); sync();
camera.position.copy(controls.target).add(new THREE.Vector3(0, 1, 0)); controls.update();
function resize() {
  const w = view.clientWidth, h = view.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h); camera.aspect = w / h; mat.uniforms.scale.value = h;
  look(camera.position.clone().sub(controls.target));
}
const observer = new ResizeObserver(resize); observer.observe(view); resize();
const hud = $('hud');
let frame;
function loop() {
  frame = requestAnimationFrame(loop); controls.update(); renderer.render(scene, camera);
  const t = controls.target;
  hud.textContent = `target x ${(t.x / VX + C[0]).toFixed(0)}  y ${(t.y / VX + C[1]).toFixed(0)}  z ${(t.z / VX + C[2]).toFixed(0)}`;
}
loop();
return () => {
  cancelAnimationFrame(frame); abort.abort(); observer.disconnect(); controls.dispose();
  scene.traverse(object => {
    object.geometry?.dispose();
    const materials = object.material ? (Array.isArray(object.material) ? object.material : [object.material]) : [];
    materials.forEach(material => material.dispose());
  });
  tex.forEach(texture => texture?.dispose()); renderer.dispose(); renderer.domElement.remove();
};
}
