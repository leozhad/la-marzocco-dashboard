import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';
import { ShotReplay } from './shot-replay.mjs';

// Exterior proportions follow the supplied white/walnut Linea Mini photograph.
// Hidden plumbing and boiler placement are schematic, not factory CAD.
export function createMachine(viewport, onSelect, { onShotRequest, onReplayUpdate } = {}) {
  const replay = new ShotReplay();
  const mobile = matchMedia('(max-width:700px)');
  const reduced = matchMedia('(prefers-reduced-motion:reduce)');
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(37, 1, 0.1, 70);
  const home = new THREE.Vector3(-4.2, 4.0, 8.3);
  camera.position.copy(home);
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, mobile.matches ? 1.6 : 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.95;
  renderer.domElement.setAttribute('aria-label', 'Interactive 3D Linea Mini');
  viewport.append(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 2.25, 0.1);
  controls.enableDamping = true;
  controls.dampingFactor = 0.09;
  controls.minDistance = 6.2;
  controls.maxDistance = 19;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.minPolarAngle = 0.12;
  controls.enablePan = false;
  controls.autoRotateSpeed = 0.5;
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const environment = pmrem.fromScene(room, 0.04);
  scene.environment = environment.texture;
  room.dispose();
  pmrem.dispose();
  scene.add(new THREE.HemisphereLight(0xd5ebef, 0x324443, 1.1));
  function light(color, intensity, position) {
    const result = new THREE.DirectionalLight(color, intensity);
    result.position.set(...position);
    scene.add(result);
    return result;
  }
  const key = light(0xfff8e9, 3, [-3, 8, 6]);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  Object.assign(key.shadow.camera, { left: -6, right: 6, top: 7, bottom: -5, near: 0.1, far: 25 });
  key.shadow.normalBias = 0.025;
  key.shadow.bias = -0.0001;
  key.shadow.radius = 3;
  light(0xc6e2ee, 2, [6, 4, -2]);
  light(0xffd3a3, 1.4, [-4, 2, -6]);

  function texture(draw, width = 512, height = width) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    draw(canvas.getContext('2d'), width, height);
    const result = new THREE.CanvasTexture(canvas);
    result.colorSpace = THREE.SRGBColorSpace;
    result.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8);
    return result;
  }
  let seed = 20260911;
  const random = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
  const woodTexture = texture((ctx, w, h) => {
    ctx.fillStyle = '#80512f';
    ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < 430; i++) {
      const y = random() * h;
      ctx.beginPath();
      ctx.strokeStyle = i % 3 ? `rgba(42,20,8,${0.04 + random() * 0.22})` : 'rgba(209,156,93,.22)';
      ctx.lineWidth = 0.5 + random() * 2;
      for (let x = 0; x <= w; x += 8) {
        const yy = y + Math.sin(x / 85 + i * 0.33) * (3 + i % 12) + Math.sin(x / 34) * 1.2;
        x ? ctx.lineTo(x, yy) : ctx.moveTo(x, yy);
      }
      ctx.stroke();
    }
  });
  const standard = (color, metalness = 0, roughness = 0.4) =>
    new THREE.MeshStandardMaterial({ color, metalness, roughness });
  const mat = {
    white: new THREE.MeshPhysicalMaterial({ color: 0xf3f0e5, metalness: 0.12, roughness: 0.27, clearcoat: 0.6 }),
    steel: standard(0xb7c4c5, 1, 0.23),
    chrome: standard(0xb0bfc0, 1, 0.16),
    brushed: standard(0xb6c0bd, 0.95, 0.36),
    black: standard(0x101819, 0.1, 0.44),
    rubber: standard(0x141817, 0, 0.75),
    wood: new THREE.MeshStandardMaterial({ map: woodTexture, color: 0xa98665, roughness: 0.46 }),
    copper: standard(0xb77240, 0.82, 0.3),
    brass: standard(0xc3a15c, 0.8, 0.33),
    ceramic: new THREE.MeshPhysicalMaterial({ color: 0xf9f7ec, roughness: 0.19, clearcoat: 0.8 }),
    red: new THREE.MeshStandardMaterial({ color: 0xbb151c, emissive: 0xe8202c, emissiveIntensity: 2 }),
    blue: new THREE.MeshStandardMaterial({ color: 0x168bdd, emissive: 0x129aff, emissiveIntensity: 2 }),
  };
  const machine = new THREE.Group();
  scene.add(machine);
  function mesh(geometry, material, parent, position = [0, 0, 0], name = '') {
    const object = new THREE.Mesh(geometry, material);
    object.position.set(...position);
    object.castShadow = true;
    object.receiveShadow = true;
    object.name = name;
    parent.add(object);
    return object;
  }
  function box(size, position, material, parent = machine, radius = 0.035, name = '') {
    const [w, h, d] = size;
    const r = Math.min(radius, w / 4, h / 4);
    const shape = new THREE.Shape();
    shape.moveTo(r, 0);
    shape.lineTo(w - r, 0); shape.quadraticCurveTo(w, 0, w, r);
    shape.lineTo(w, h - r); shape.quadraticCurveTo(w, h, w - r, h);
    shape.lineTo(r, h); shape.quadraticCurveTo(0, h, 0, h - r);
    shape.lineTo(0, r); shape.quadraticCurveTo(0, 0, r, 0);
    const bevel = Math.min(0.018, d / 5);
    const geometry = new THREE.ExtrudeGeometry(shape, {
      depth: d - bevel * 2, bevelEnabled: true, bevelSize: bevel,
      bevelThickness: bevel, bevelSegments: 2, steps: 1, curveSegments: 5,
    });
    geometry.center();
    return mesh(geometry, material, parent, position, name);
  }
  function cylinder(radius, height, position, material, parent = machine, axis = 'y', name = '') {
    const object = mesh(new THREE.CylinderGeometry(radius, radius, height, 48), material, parent, position, name);
    if (axis === 'z') object.rotation.x = Math.PI / 2;
    if (axis === 'x') object.rotation.z = Math.PI / 2;
    return object;
  }
  function woodProfile(shape, depth, position, material, parent, name) {
    const geometry = new THREE.ExtrudeGeometry(shape, {
      depth, bevelEnabled: true, bevelSize: 0.028, bevelThickness: 0.028,
      bevelSegments: 4, curveSegments: 16, steps: 1,
    });
    geometry.translate(0, 0, -depth / 2);
    geometry.computeBoundingBox();
    const bounds = geometry.boundingBox;
    const size = bounds.getSize(new THREE.Vector3());
    const vertices = geometry.attributes.position, normals = geometry.attributes.normal, uv = geometry.attributes.uv;
    for (let i = 0; i < vertices.count; i++) {
      const x = (vertices.getX(i) - bounds.min.x) / size.x;
      const y = (vertices.getY(i) - bounds.min.y) / size.y;
      const z = (vertices.getZ(i) - bounds.min.z) / size.z;
      if (Math.abs(normals.getZ(i)) > .5) uv.setXY(i, x, y);
      else if (Math.abs(normals.getY(i)) > .5) uv.setXY(i, x, z);
      else uv.setXY(i, z, y);
    }
    return mesh(geometry, material, parent, position, name);
  }
  function tube(points, radius, material, parent = machine) {
    const curve = new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p)));
    return mesh(new THREE.TubeGeometry(curve, 32, radius, 10, false), material, parent);
  }
  function bolt(position, parent = machine) {
    const object = cylinder(0.045, 0.02, position, mat.chrome, parent, 'z');
    box([0.044, 0.008, 0.006], [position[0], position[1], position[2] + 0.014], mat.black, parent, 0);
    return object;
  }
  const panels = [];
  function panel(name, position, offset, hideInside = true) {
    const object = new THREE.Group();
    object.name = name;
    object.position.set(...position);
    machine.add(object);
    panels.push({ object, base: object.position.clone(), offset: new THREE.Vector3(...offset), hideInside });
    return object;
  }

  // White cabinet and stainless chassis. The front is open beneath the fascia.
  box([3.48, 0.19, 3.95], [0, 0.48, -0.15], mat.steel);
  for (const x of [-1.45, 1.45]) for (const z of [-1.65, 1.78])
    cylinder(0.18, 0.22, [x, 0.23, z], mat.rubber);
  for (const side of [-1, 1]) {
    const shell = panel(side < 0 ? 'left-white-panel' : 'right-white-panel',
      [side * 1.74, 3.04, -0.12], [side * 1.02, 0, 0]);
    box([0.11, 1.26, 3.5], [0, 0, 0], mat.white, shell, 0.07);
    box([0.06, 1.18, 0.045], [-side * 0.07, 0, 1.75], mat.chrome, shell);
    const lower=panel(`${side<0?'left':'right'}-lower-chassis`,[0,0,0],[side*.9,0,0]);
    const shape=new THREE.Shape();
    shape.moveTo(side*1.42,.55);shape.lineTo(side*1.68,2.43);
    shape.lineTo(side*1.75,2.43);shape.lineTo(side*1.49,.55);shape.closePath();
    const geo=new THREE.ExtrudeGeometry(shape,{depth:3.45,bevelEnabled:false});
    geo.translate(0,0,-1.9);mesh(geo,mat.white,lower);
  }
  const back = panel('rear-white-panel', [0, 3.04, -1.94], [0, 0, -0.85]);
  box([3.42, 1.26, 0.1], [0, 0, 0], mat.white, back, 0.08);
  const lowerBack=panel('rear-lower-chassis',[0,1.49,-1.91],[0,0,-.85]);
  box([2.96,1.83,.09],[0,0,0],mat.white,lowerBack);
  // Rear ventilation details remain visible when orbiting around the real model.
  for (let i = 0; i < 9; i++) box([1.45, 0.018, 0.012], [0, -0.35 + i * 0.082, -0.058], mat.black, back, 0.002);
  const deck = panel('cup-deck', [0, 3.66, -0.14], [0, 1.15, 0]);
  box([3.44, 0.12, 3.5], [0, 0, 0], mat.white, deck, 0.08);
  box([3.16, 0.025, 3.32], [0, 0.08, 0], mat.brushed, deck);
  for (let i = -12; i <= 12; i++)
    cylinder(0.016, 3.3, [i * 0.12, 0.105, 0], mat.chrome, deck, 'z');
  for (const x of [-1.63, 1.63]) {
    cylinder(0.025, 3.5, [x, 0.22, -0.08], mat.chrome, deck, 'z');
    for (const z of [-1.7, 1.6]) cylinder(0.025, 0.17, [x, 0.15, z], mat.chrome, deck);
  }
  cylinder(0.025, 3.25, [0, 0.22, -1.82], mat.chrome, deck, 'x');

  const front = panel('upper-front-controls', [0, 3.04, 1.78], [0, 0.08, 0.85], false);
  const fascia = box([3.49, 1.12, 0.16], [0, 0, 0], mat.white, front, 0.08, 'white-fascia');
  for (const x of [-1.31, 1.31]) {
    cylinder(0.325, 0.06, [x, 0, 0.12], mat.chrome, front, 'z', 'metal-control-ring');
    cylinder(0.27, 0.16, [x, 0, 0.21], mat.brushed, front, 'z', 'brushed-control-knob');
    cylinder(0.21, 0.01, [x, 0, 0.297], mat.brushed, front, 'z');
    box([0.01, 0.12, 0.006], [x, 0.13, 0.307], mat.steel, front, 0.002);
  }
  box([1.52, 0.44, 0.085], [0, -0.01, 0.14], mat.black, front, 0.065);
  const mountShape = new THREE.Shape();
  mountShape.moveTo(.46,.29); mountShape.quadraticCurveTo(.46,.34,.53,.32);
  mountShape.lineTo(.92,.2); mountShape.quadraticCurveTo(.95,.18,.95,.12);
  mountShape.lineTo(.93,-.17); mountShape.quadraticCurveTo(.92,-.21,.86,-.2);
  mountShape.lineTo(.49,-.15); mountShape.quadraticCurveTo(.45,-.13,.46,-.07);
  mountShape.closePath();
  const mountWood=mat.wood.clone(); mountWood.color.setHex(0x805d42);
  woodProfile(mountShape,.12,[0,0,.21],mountWood,front,'sculpted-walnut-paddle-mount');
  const paddlePivot = new THREE.Group();paddlePivot.position.set(.54,0,.22);front.add(paddlePivot);
  const paddleShape = new THREE.Shape();
  paddleShape.moveTo(-.77,.17);
  paddleShape.bezierCurveTo(-.37,.22,.18,.2,.44,.13);
  paddleShape.quadraticCurveTo(.51,.1,.49,.035);
  paddleShape.lineTo(.46,-.1);
  paddleShape.bezierCurveTo(.1,-.2,-.39,-.23,-.77,-.17);
  paddleShape.quadraticCurveTo(-.84,-.15,-.84,-.06);
  paddleShape.lineTo(-.84,.075);
  paddleShape.quadraticCurveTo(-.83,.15,-.77,.17);
  const paddleWood=mat.wood.clone();paddleWood.color.setHex(0x9c7954);paddleWood.roughness=.38;
  const paddle=woodProfile(paddleShape,.235,[-.54,0,.13],paddleWood,paddlePivot,'contoured-walnut-brew-paddle');
  paddle.userData.action='shot';
  for(const [x,y] of [[.54,.245],[.56,-.11]]) {
    cylinder(.027,.014,[x,y,.291],mat.brushed,front,'z');
    box([.029,.005,.005],[x,y,.303],mat.black,front,.001);
  }
  for (const [y, material] of [[0.15, mat.red], [-0.12, mat.blue]]) {
    cylinder(0.062, 0.016, [-0.89, y, 0.091], mat.chrome, front, 'z');
    mesh(new THREE.SphereGeometry(0.043, 16, 10), material, front, [-0.89, y, 0.105]);
  }
  const steelPanel = panel('polished-front-panel', [0, 1.62, 1.59], [0, 0, 0.45]);
  box([3.25, 1.64, 0.09], [0, 0, 0], mat.chrome, steelPanel, 0.07);
  for (const x of [-1.48, 1.48]) for (const y of [-0.68, 0.67]) bolt([x, y, 0.055], steelPanel);

  function gauge(x, max, name) {
    cylinder(0.23, 0.05, [x, 1.36, 1.685], mat.chrome, machine, 'z', name);
    const face = texture((ctx, w, h) => {
      const c = w / 2; ctx.fillStyle = '#eeeadd'; ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = '#404846'; ctx.fillStyle = '#303a39'; ctx.textAlign = 'center';
      for (let i = 0; i <= 32; i++) {
        const a = Math.PI * 0.75 + i / 32 * Math.PI * 1.5;
        const long = i % 4 === 0;
        ctx.lineWidth = long ? 4 : 2;
        ctx.beginPath(); ctx.moveTo(c + Math.cos(a) * 204, c + Math.sin(a) * 204);
        ctx.lineTo(c + Math.cos(a) * (long ? 172 : 187), c + Math.sin(a) * (long ? 172 : 187)); ctx.stroke();
        if (long) { ctx.font = '29px Arial'; ctx.fillText((max * i / 32).toFixed(max < 5 ? 1 : 0), c + Math.cos(a) * 139, c + Math.sin(a) * 139 + 9); }
      }
      ctx.font = '25px Arial'; ctx.fillText('bar', c, 342);
      ctx.font = 'bold 22px Georgia'; ctx.fillText('LA MARZOCCO', c, 392);
      // A static gauge illustration, intentionally not driven by inferred pressure.
      ctx.strokeStyle = '#6f3c30'; ctx.lineWidth = 9; ctx.beginPath();ctx.moveTo(c, c);ctx.lineTo(110, 395);ctx.stroke();
      ctx.fillStyle = '#4b4b42';ctx.beginPath();ctx.arc(c,c,16,0,Math.PI*2);ctx.fill();
    });
    const material = new THREE.MeshBasicMaterial({ map: face });
    mesh(new THREE.CircleGeometry(0.202, 64), material, machine, [x, 1.36, 1.714]);
  }
  gauge(-1.18, 3, 'steam-pressure-gauge');
  gauge(1.18, 18, 'brew-pressure-gauge');

  // Chrome group, twin spouts, and the long walnut portafilter seen in the photo.
  const group = new THREE.Group(); group.userData.component = 'group'; machine.add(group);
  for (const [y, radius, height] of [[2.45, 0.48, 0.13], [2.31, 0.38, 0.18], [2.18, 0.44, 0.09], [2.08, 0.37, 0.1]])
    cylinder(radius, height, [0, y, 1.89], mat.chrome, group);
  for (let i = 0; i < 12; i++) {
    const angle = i / 12 * Math.PI * 2;
    cylinder(0.024, 0.11, [Math.cos(angle) * 0.39, 2.3, 1.89 + Math.sin(angle) * 0.39], mat.steel, group);
  }
  cylinder(0.17, 0.12, [0, 1.98, 1.91], mat.brushed, group);
  tube([[0, 1.93, 1.91], [-0.1, 1.89, 2.02], [-0.23, 1.78, 2.08]], 0.047, mat.chrome, group);
  tube([[0, 1.93, 1.91], [0.1, 1.89, 2.02], [0.23, 1.78, 2.08]], 0.047, mat.chrome, group);
  const handle = new THREE.Group(); handle.position.set(0.24, 2.12, 2.07);
  handle.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0.55, -0.29, 1).normalize());
  group.add(handle);
  cylinder(0.095, 0.3, [0, 0.15, 0], mat.chrome, handle);
  const profile = [[0,0.25],[0.105,0.25],[0.14,0.32],[0.155,0.47],[0.18,0.9],[0.18,1.17],[0.14,1.24],[0,1.26]];
  const handleWood=mat.wood.clone();
  handleWood.map=woodTexture.clone();handleWood.map.rotation=Math.PI/2;handleWood.map.center.set(.5,.5);handleWood.map.needsUpdate=true;
  mesh(new THREE.LatheGeometry(profile.map(p => new THREE.Vector2(...p)), 48), handleWood, handle, [0,0,0], 'walnut-portafilter-handle');
  cylinder(0.02, 0.005, [0, 1.265, 0], mat.brass, handle);

  // Right steam wand, black grip, and compact left hot-water outlet.
  tube([[1.25,2.51,1.76],[1.42,2.3,1.89],[1.6,2.13,2.1],[1.6,1.02,2.2],[1.51,0.86,2.24]], 0.04, mat.chrome);
  tube([[1.45,2.27,1.94],[1.56,2.12,2.07],[1.59,1.89,2.13]], 0.075, mat.rubber);
  cylinder(0.06, 0.15, [1.52,0.86,2.24], mat.brushed);
  tube([[-1.08,2.48,1.69],[-1.11,2.28,1.88],[-1.09,2.06,1.96]], 0.066, mat.chrome);
  cylinder(0.095, 0.12, [-1.09,2.06,1.96], mat.brushed);
  box([0.11,0.3,0.07],[-1.39,2.2,1.72],mat.black);

  // Recessed scale tray: the Connected Scale sits in a cutout, flush with the grille.
  box([3.63,0.45,1.4],[0,0.48,1.96],mat.white,machine,0.07);
  for(const x of [-1.145,1.145]) {
    box([1.18,0.06,1.31],[x,0.73,1.96],mat.chrome);
    box([1.03,0.04,1.12],[x,0.76,1.96],mat.black);
  }
  for(const z of [1.335,2.585])box([3.49,.06,.06],[0,.73,z],mat.chrome);
  box([1.13,.025,1.11],[0,.625,1.97],mat.brushed,machine,.015,'recessed-scale-support');
  for(const x of [-.565,.565])box([.025,.17,1.11],[x,.715,1.97],mat.brushed);
  for(let i=-14;i<=14;i++)if(Math.abs(i*.111)>.58)box([0.018,0.025,1.13],[i*0.111,0.79,1.96],mat.brushed);
  for(const z of [1.39,2.51])box([3.32,0.028,0.03],[0,0.795,z],mat.chrome);
  const scale = box([1.05,0.15,1.05],[0,0.72,1.97],mat.black,machine,0.065,'lamarzocco-connected-scale');
  scale.userData.component='scale';
  box([1.0,0.018,0.77],[0,0.807,1.84],mat.black);
  box([0.97,0.009,0.22],[0,0.8,2.365],standard(0x0c1416,0.35,0.14));
  const scaleFace=texture((ctx,w,h)=>{
    ctx.clearRect(0,0,w,h);ctx.strokeStyle='#73817f';ctx.lineWidth=3;
    ctx.beginPath();ctx.arc(48,48,14,.3,Math.PI*2-.3);ctx.stroke();
    ctx.beginPath();ctx.moveTo(48,26);ctx.lineTo(48,46);ctx.stroke();
    ctx.fillStyle='#73817f';ctx.font='34px Arial';ctx.fillText('T',w-70,60);
  },512,96);
  const scaleGlass=mesh(new THREE.PlaneGeometry(.94,.18),new THREE.MeshBasicMaterial({map:scaleFace,transparent:true,depthWrite:false}),machine,[0,.809,2.365]);
  scaleGlass.rotation.x=-Math.PI/2;
  const scaleBrand=texture((ctx,w,h)=>{
    ctx.clearRect(0,0,w,h);ctx.fillStyle='#b8c4be';ctx.textAlign='center';
    ctx.font='italic bold 35px Georgia';ctx.fillText('la marzocco',w/2,45);
    ctx.font='18px Arial';ctx.fillText('HOME',w/2,72);
  },384,96);
  mesh(new THREE.PlaneGeometry(.36,.09),new THREE.MeshBasicMaterial({map:scaleBrand,transparent:true,depthWrite:false}),machine,[.28,.715,2.504]);
  const logo = texture((ctx,w,h)=>{
    ctx.clearRect(0,0,w,h);ctx.fillStyle='#a41220';ctx.font='900 96px Arial Black, Arial';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('LA MARZOCCO',w/2,h/2);
  },1024,128);
  mesh(new THREE.PlaneGeometry(1.43,0.18),new THREE.MeshBasicMaterial({map:logo,transparent:true,depthWrite:false}),machine,[0.77,0.43,2.675]);

  // Cups and a small wooden-handled tool on the warming deck.
  function cup(x,z,y,radius=0.28,parent=deck) {
    const shape=[[0,0],[radius*.7,0],[radius*.82,.08],[radius,.4],[radius,.43],[radius-.035,.43],[radius-.04,.12],[0,.12]];
    mesh(new THREE.LatheGeometry(shape.map(p=>new THREE.Vector2(...p)),40),mat.ceramic,parent,[x,y,z],'white-cup');
    const ring=mesh(new THREE.TorusGeometry(.14,.032,10,32),mat.ceramic,parent,[x+radius+.09,y+.24,z]);ring.rotation.y=Math.PI/2;
  }
  cup(.48,-.45,.14,.3);cup(.48,-.45,.49,.31);cup(-.2,-.85,.14,.27);
  cylinder(.18,.09,[-.85,.19,.1],mat.chrome,deck);
  cylinder(.105,.32,[-.85,.39,.1],mat.wood,deck);

  // Schematic internal components for cutaway/exploded exploration.
  const internals = new THREE.Group();machine.add(internals);
  const boiler=cylinder(.74,2.65,[0,2.18,-.75],mat.brushed,internals,'x','steam-boiler');
  boiler.userData.component='boiler';
  for(const x of [-1.32,1.32])cylinder(.76,.06,[x,2.18,-.75],mat.chrome,internals,'x');
  for(const x of [-.94,.94])cylinder(.757,.1,[x,2.18,-.75],mat.steel,internals,'x');
  box([.66,.53,.72],[0,2.67,1.16],mat.brushed,internals,.045,'integrated-brew-boiler').userData.component='boiler';
  cylinder(.28,.06,[0,2.96,1.16],mat.chrome,internals);
  const pump=cylinder(.31,.73,[-.79,1.07,-.9],mat.black,internals,'z','pump-motor');
  pump.userData.component='pump';
  cylinder(.22,.24,[-.79,1.07,-.42],mat.brass,internals,'z');
  const brewFeed=tube([[-.79,1.07,-.25],[-.79,1.25,.5],[-.35,2.16,.67],[0,2.4,1.02]],.038,mat.copper,internals);
  tube([[.95,2.4,-.75],[1.35,2.6,-.5],[1.36,2.74,.8],[1.25,2.5,1.76]],.043,mat.copper,internals);
  const groupFeed=tube([[0,2.72,1.02],[0,2.77,1.6],[0,2.5,1.89]],.05,mat.copper,internals);
  const drain=tube([[.26,2.48,1.27],[.76,2.22,1.35],[.84,1.25,1.36],[.83,.84,1.7]],.032,mat.copper,internals);
  box([.17,.22,.2],[.28,2.53,1.26],mat.black,internals,.015,'three-way-drain-valve');

  // Main controller and a separate ESP32 gateway. The installation guide shows
  // a serial gateway connection; placement and PCB components are illustrative.
  const electronics = new THREE.Group();electronics.userData.component='iot';internals.add(electronics);
  const pcb=standard(0x18563f,.12,.58),terminal=standard(0x427f48,.05,.6);
  box([1.04,1.14,.035],[.32,2.73,-1.62],pcb,electronics,.015,'connected-machine-controller');
  box([1.13,1.23,.025],[.32,2.73,-1.66],mat.brushed,electronics,.02);
  for(let i=0;i<7;i++) {
    box([.13,.095,.11],[-.11,2.28+i*.13,-1.54],terminal,electronics,.008);
    cylinder(.016,.008,[-.11,2.28+i*.13,-1.477],mat.brushed,electronics,'z');
  }
  for(const [x,y] of [[.22,2.68],[.52,2.68],[.23,2.98]])box([.22,.15,.13],[x,y,-1.53],mat.black,electronics,.008);
  for(const [x,y] of [[.65,2.28],[.46,2.35],[.63,3.12]])cylinder(.065,.13,[x,y,-1.54],mat.black,electronics,'z');
  for(let i=0;i<5;i++)box([.12,.07,.06],[.74,2.51+i*.13,-1.555],mat.ceramic,electronics,.005);
  const gateway=new THREE.Group();gateway.position.set(1.03,3.16,-1.03);gateway.rotation.y=-.18;electronics.add(gateway);
  box([.66,.42,.025],[0,0,0],pcb,gateway,.016,'esp32-gateway-pcb');
  box([.26,.24,.045],[-.06,-.015,.04],mat.brushed,gateway,.01,'esp32-radio-shield');
  const chipLabel=texture((ctx,w,h)=>{ctx.clearRect(0,0,w,h);ctx.fillStyle='#293733';ctx.font='bold 43px Arial';ctx.textAlign='center';ctx.fillText('ESP32',w/2,h*.65);},256,96);
  mesh(new THREE.PlaneGeometry(.23,.087),new THREE.MeshBasicMaterial({map:chipLabel,transparent:true,depthWrite:false}),gateway,[-.06,-.012,.065]);
  for(let i=0;i<5;i++) {
    box([.09,.012,.006],[.235,-.12+i*.06,.02],mat.brass,gateway,.002);
    if(i<4)box([.012,.058,.006],[i%2?.274:.196,-.09+i*.06,.02],mat.brass,gateway,.002);
  }
  for(const x of [-.3,.3])for(const y of [-.18,.18])cylinder(.022,.008,[x,y,.02],mat.brass,gateway,'z');
  const gatewayLedMaterial=new THREE.MeshStandardMaterial({color:0x76bd86,emissive:0x5fd184,emissiveIntensity:.7});
  mesh(new THREE.SphereGeometry(.022,12,8),gatewayLedMaterial,gateway,[-.26,.1,.035]);
  for(const [i,color] of [0xbb3435,0x2f74a7,0xe7e7d6,0x1d2424].entries()) {
    tube([[.7,3.14-i*.04,-1.49],[.78,3.35-i*.02,-1.3],[.86,3.07+i*.035,-1.005]],.011,standard(color,0,.7),electronics);
  }
  const pumpBase=pump.position.clone();
  const replayCup=new THREE.Group();replayCup.position.set(0,.83,2.1);machine.add(replayCup);cup(0,0,0,.29,replayCup);replayCup.visible=false;
  const coffeeMaterial=standard(0x8b4524,0,.43);
  const coffee=mesh(new THREE.CircleGeometry(.23,48),coffeeMaterial,replayCup,[0,.126,0]);
  coffee.rotation.x=-Math.PI/2;
  const streams=new THREE.Group();machine.add(streams);
  for(const x of [-.18,.18])cylinder(.012,.51,[x,1.525,2.08],coffeeMaterial,streams);
  streams.visible=false;
  const flowGeometry=new THREE.SphereGeometry(.047,10,8);
  function flowPath(tubeMesh,color,count) {
    tubeMesh.material=tubeMesh.material.clone();
    tubeMesh.material.transparent=true;tubeMesh.material.depthWrite=false;
    const material=new THREE.MeshBasicMaterial({color,transparent:true,opacity:.95,depthWrite:false});
    const particles=Array.from({length:count},()=>mesh(flowGeometry,material,internals));
    particles.forEach(p=>{p.castShadow=false;p.visible=false;});
    return {curve:tubeMesh.geometry.parameters.path,particles,tube:tubeMesh};
  }
  const flows=[flowPath(brewFeed,0x84d4eb,8),flowPath(groupFeed,0xf3c688,5),flowPath(drain,0xba8a55,6)];
  let lastReplayPaint=-1,wasReplayVisible=false;
  function paintScale(snapshot) {
    const ctx=scaleFace.image.getContext('2d'),w=scaleFace.image.width,h=scaleFace.image.height;
    ctx.clearRect(0,0,w,h);ctx.strokeStyle='#73817f';ctx.lineWidth=3;
    ctx.beginPath();ctx.arc(35,48,11,.3,Math.PI*2-.3);ctx.stroke();
    ctx.beginPath();ctx.moveTo(35,29);ctx.lineTo(35,46);ctx.stroke();
    ctx.fillStyle='#73817f';ctx.font='27px Arial';ctx.fillText('T',w-35,58);
    if(snapshot.status!=='idle') {
      ctx.fillStyle='#e0e8de';ctx.font='42px monospace';ctx.textAlign='center';
      ctx.fillText(snapshot.elapsed.toFixed(1),153,63);ctx.fillText(snapshot.yield.toFixed(1),354,63);ctx.textAlign='start';
    }
    scaleFace.needsUpdate=true;
  }
  function animateReplay(snapshot,dt,time) {
    const visible=snapshot.status!=='idle';
    replayCup.visible=visible;
    const opening=snapshot.pumpOn ? .46 : 0;
    paddlePivot.rotation.y=reduced.matches?opening:THREE.MathUtils.lerp(paddlePivot.rotation.y,opening,1-Math.exp(-dt*13));
    pump.position.copy(pumpBase);
    if(snapshot.pumpOn&&!reduced.matches)pump.position.x+=Math.sin(snapshot.elapsed*90)*.007;
    coffee.position.y=.126+Math.min(snapshot.yield/70,.85)*.25;
    streams.visible=snapshot.pumpOn&&snapshot.elapsed>Math.min(.8,snapshot.duration*.1);
    for(const [index,flow] of flows.entries()) {
      const active=index===2?snapshot.status==='draining':snapshot.pumpOn;
      flow.tube.material.opacity=active ? .3 : 1;
      flow.particles.forEach((particle,i)=>{
        particle.visible=active&&!reduced.matches;
        if(particle.visible)particle.position.copy(flow.curve.getPointAt((snapshot.elapsed*.75+snapshot.drainProgress+i/flow.particles.length)%1));
      });
    }
    gatewayLedMaterial.emissiveIntensity=snapshot.active&&!reduced.matches ? .8+Math.sin(snapshot.elapsed*9)*.5 : .5;
    if(time-lastReplayPaint>90||visible!==wasReplayVisible||!snapshot.active) {
      paintScale(snapshot);onReplayUpdate?.(snapshot);lastReplayPaint=time;wasReplayVisible=visible;
    }
  }

  const floor=mesh(new THREE.PlaneGeometry(18,18),new THREE.ShadowMaterial({opacity:.3}),scene,[0,.09,0]);
  floor.rotation.x=-Math.PI/2;floor.castShadow=false;
  for(const radius of [3.5,4.1]) {
    const ring=mesh(new THREE.RingGeometry(radius,radius+.01,120),new THREE.MeshBasicMaterial({color:0x547473,transparent:true,opacity:.17,side:THREE.DoubleSide,depthWrite:false}),scene,[0,.08,0]);
    ring.rotation.x=-Math.PI/2;ring.castShadow=false;
  }
  const anchors={boiler:new THREE.Vector3(-.08,2.75,1.2),group:new THREE.Vector3(0,2.16,2.1),scale:new THREE.Vector3(0,.83,2.18),iot:new THREE.Vector3(1.03,3.43,-.96)};
  const focusAnchors={...anchors,iot:new THREE.Vector3(1.03,3.16,-.96)};
  const state={mode:'assembled',interactive:!mobile.matches,visible:true,contextLost:false};
  let frame=0,lastTime=0,dragging=false,damping=0;
  const project=new THREE.Vector3();
  function hotspots() {
    for(const [name,anchor] of Object.entries(anchors)) {
      project.copy(anchor).project(camera);
      const element=viewport.parentElement.querySelector(`[data-component="${name}"]`);
      const x=(project.x+1)*viewport.clientWidth/2;
      const y=(-project.y+1)*viewport.clientHeight/2;
      element.style.left=`${x-22}px`;element.style.top=`${y+viewport.offsetTop-22}px`;
      element.hidden=project.z>1||x<0||x>viewport.clientWidth||y<0||y>viewport.clientHeight||state.mode==='exploded'||(['iot','boiler'].includes(name)&&state.mode==='assembled');
    }
  }
  function request() { if(!frame && state.visible && !document.hidden && !state.contextLost)frame=requestAnimationFrame(render); }
  function render(time) {
    frame=0;
    const elapsedSeconds=lastTime?Math.max(0,(time-lastTime)/1000):0;
    const dt=Math.min(elapsedSeconds || .016,.05);lastTime=time;
    let moving=false;
    for(const part of panels) {
      const target=part.base.clone();
      if(state.mode==='exploded')target.add(part.offset);
      if(part.object.position.distanceTo(target)>.001) {part.object.position.lerp(target,reduced.matches?1:1-Math.exp(-dt*9));moving=true;}
      part.object.visible=!(state.mode==='cutaway'&&part.hideInside);
    }
    fascia.visible=state.mode!=='cutaway';
    const replayState=replay.advance(elapsedSeconds);
    animateReplay(replayState,dt,time);
    controls.update(dt);hotspots();renderer.render(scene,camera);
    if(moving||dragging||controls.autoRotate||replayState.active||Math.abs(paddlePivot.rotation.y-(replayState.pumpOn ? .46 : 0))>.001||damping-->0)request();
  }
  controls.addEventListener('change',request);
  controls.addEventListener('start',()=>{dragging=true;request();});
  controls.addEventListener('end',()=>{dragging=false;damping=16;request();});
  function resize() {
    if(!viewport.clientWidth||!viewport.clientHeight)return;
    camera.aspect=viewport.clientWidth/viewport.clientHeight;
    camera.fov=mobile.matches?43:37;camera.updateProjectionMatrix();
    renderer.setSize(viewport.clientWidth,viewport.clientHeight);request();
  }
  new ResizeObserver(resize).observe(viewport);
  new IntersectionObserver(entries=>{state.visible=entries[0].isIntersecting;if(state.visible){lastTime=0;resize();request();}}).observe(viewport);
  document.addEventListener('visibilitychange',()=>{lastTime=0;if(document.hidden){replay.pause();onReplayUpdate?.(replay.snapshot());}request();});
  renderer.domElement.addEventListener('webglcontextlost',event=>{event.preventDefault();state.contextLost=true;viewport.classList.add('context-lost');document.getElementById('model-loading').textContent='3D paused. Reload the page to restore the model.';document.getElementById('model-loading').hidden=false;});
  function interaction(enabled) {
    state.interactive=enabled;controls.enabled=enabled;
    renderer.domElement.style.touchAction=enabled?'none':'pan-y';
    document.getElementById('interact-model').setAttribute('aria-pressed',String(enabled));
    document.getElementById('interact-model').textContent=enabled?'Done rotating':'Interact with 3D';
  }
  interaction(!mobile.matches);
  mobile.addEventListener('change',()=>{interaction(!mobile.matches);resize();});
  document.getElementById('interact-model').addEventListener('click',()=>interaction(!state.interactive));
  const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();let down;
  renderer.domElement.addEventListener('pointerdown',event=>{down=[event.clientX,event.clientY];});
  renderer.domElement.addEventListener('pointerup',event=>{
    if(!down||Math.hypot(event.clientX-down[0],event.clientY-down[1])>5)return;
    const rect=renderer.domElement.getBoundingClientRect();
    pointer.set((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);
    raycaster.setFromCamera(pointer,camera);
    for(const hit of raycaster.intersectObject(machine,true)){
      let ancestor=hit.object,visible=true;
      while(ancestor){if(!ancestor.visible)visible=false;ancestor=ancestor.parent;}
      if(!visible)continue;
      let object=hit.object;while(object&&!object.userData.component&&!object.userData.action)object=object.parent;
      if(object){if(object.userData.action==='shot')onShotRequest?.();else onSelect(object.userData.component);break;}
      break;
    }
  });
  function mode(value) {
    const wasExploded=state.mode==='exploded';
    const offset=camera.position.clone().sub(controls.target);
    if(value==='exploded'&&!wasExploded)offset.multiplyScalar(1.2);
    if(value!=='exploded'&&wasExploded)offset.divideScalar(1.2);
    state.mode=value;
    document.querySelectorAll('[data-mode]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.mode===value)));
    document.getElementById('model-hint').textContent=value==='assembled'?'DRAG TO ORBIT · CLICK THE PADDLE TO REPLAY A SHOT':'INTERNAL LAYOUT IS SCHEMATIC · SELECT THE IOT GATEWAY';
    if(value==='exploded'){controls.target.set(0,2.5,0);}
    else{controls.target.set(0,2.25,.1);}
    camera.position.copy(controls.target).add(offset);
    request();
  }
  document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>mode(button.dataset.mode)));
  document.querySelectorAll('[data-camera]').forEach(button=>button.addEventListener('click',()=>{
    controls.minDistance=6.2;
    const preset=button.dataset.camera;
    camera.position.set(...(preset==='front'?[0,2.9,10.5]:preset==='top'?[0,10.8,.7]:home.toArray()));
    controls.target.set(0,2.25,.1);damping=15;request();
  }));
  document.getElementById('rotate-model').addEventListener('click',event=>{
    controls.autoRotate=!controls.autoRotate;event.currentTarget.setAttribute('aria-pressed',String(controls.autoRotate));request();
  });
  reduced.addEventListener('change',()=>{if(reduced.matches){controls.autoRotate=false;document.getElementById('rotate-model').setAttribute('aria-pressed','false');}request();});
  document.getElementById('model-loading').hidden=true;
  resize();
  function paddleScreenPoint() {
    const point=paddle.localToWorld(new THREE.Vector3(-.25,.015,.15)).project(camera);
    const rect=viewport.getBoundingClientRect();
    return {x:rect.left+(point.x+1)*rect.width/2,y:rect.top+(1-point.y)*rect.height/2};
  }
  return {
    mode,resize,
    toggleReplay(shot){const snapshot=replay.toggle(shot);lastTime=0;onReplayUpdate?.(snapshot);request();return snapshot;},
    resetReplay(){const snapshot=replay.reset();onReplayUpdate?.(snapshot);request();},
    pauseReplay(){const snapshot=replay.pause();onReplayUpdate?.(snapshot);request();},
    setReplaySpeed(value){replay.setSpeed(value);onReplayUpdate?.(replay.snapshot());},
    view(){return {mode:state.mode,camera:camera.position.toArray(),target:controls.target.toArray(),minDistance:controls.minDistance};},
    restoreView(view){controls.minDistance=view.minDistance??6.2;mode(view.mode);camera.position.fromArray(view.camera);controls.target.fromArray(view.target);request();},
    focus(name){if(focusAnchors[name]){controls.minDistance=2;controls.target.copy(focusAnchors[name]);camera.position.copy(focusAnchors[name]).add(new THREE.Vector3(1.7,.75,2));request();}},
    update(data){mat.red.emissiveIntensity=data.status?.power_on?2:0;mat.blue.emissiveIntensity=data.status?.power_on?2:0;request();},
    diagnostics(){return {mode:state.mode,interactive:state.interactive,visible:state.visible,contextLost:state.contextLost,autoRotate:controls.autoRotate,camera:camera.position.toArray(),gauges:2,woodenControls:2,cups:3,iotGateway:true,replay:replay.snapshot(),paddleAngle:paddlePivot.rotation.y,paddleScreen:paddleScreenPoint(),triangles:renderer.info.render.triangles,renderCalls:renderer.info.render.calls};},
  };
}
