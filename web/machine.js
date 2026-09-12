import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { RoomEnvironment } from './vendor/RoomEnvironment.js';

// Exterior proportions follow the supplied white/walnut Linea Mini photograph.
// Hidden plumbing and boiler placement are schematic, not factory CAD.
export function createMachine(viewport, onSelect) {
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
    geo.translate(0,0,-1.9);mesh(geo,mat.black,lower);
  }
  const back = panel('rear-white-panel', [0, 3.04, -1.94], [0, 0, -0.85]);
  box([3.42, 1.26, 0.1], [0, 0, 0], mat.white, back, 0.08);
  const lowerBack=panel('rear-lower-chassis',[0,1.49,-1.91],[0,0,-.85]);
  box([2.96,1.83,.09],[0,0,0],mat.black,lowerBack);
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
  box([1.34, 0.41, 0.1], [0.1, -0.005, 0.15], mat.black, front, 0.06);
  box([0.24, 0.49, 0.14], [0.72, 0.035, 0.21], mat.wood, front, 0.03, 'walnut-paddle-mount').rotation.z = -0.12;
  const paddle = box([1.1, 0.25, 0.19], [0.015, 0.035, 0.3], mat.wood, front, 0.065, 'walnut-brew-paddle');
  paddle.rotation.y = -0.04;
  bolt([0.74, 0.16, 0.3], front);
  bolt([0.71, -0.075, 0.3], front);
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

  // Drip tray, Acaia-style black scale, front red wordmark.
  box([3.63,0.45,1.4],[0,0.48,1.96],mat.white,machine,0.07);
  box([3.49,0.06,1.31],[0,0.73,1.96],mat.chrome);
  box([3.3,0.04,1.12],[0,0.76,1.96],mat.black);
  for(let i=-14;i<=14;i++)box([0.018,0.025,1.13],[i*0.111,0.79,1.96],mat.brushed);
  for(const z of [1.39,2.51])box([3.32,0.028,0.03],[0,0.795,z],mat.chrome);
  const scale = box([1.05,0.15,1.05],[0,0.88,2.01],mat.black,machine,0.065,'lamarzocco-connected-scale');
  scale.userData.component='scale';
  box([1.0,0.018,0.77],[0,0.967,1.88],mat.black);
  box([0.97,0.009,0.22],[0,0.96,2.405],standard(0x0c1416,0.35,0.14));
  const scaleFace=texture((ctx,w,h)=>{
    ctx.clearRect(0,0,w,h);ctx.strokeStyle='#73817f';ctx.lineWidth=3;
    ctx.beginPath();ctx.arc(48,48,14,.3,Math.PI*2-.3);ctx.stroke();
    ctx.beginPath();ctx.moveTo(48,26);ctx.lineTo(48,46);ctx.stroke();
    ctx.fillStyle='#73817f';ctx.font='34px Arial';ctx.fillText('T',w-70,60);
  },512,96);
  const scaleGlass=mesh(new THREE.PlaneGeometry(.94,.18),new THREE.MeshBasicMaterial({map:scaleFace,transparent:true,depthWrite:false}),machine,[0,.969,2.405]);
  scaleGlass.rotation.x=-Math.PI/2;
  const scaleBrand=texture((ctx,w,h)=>{
    ctx.clearRect(0,0,w,h);ctx.fillStyle='#b8c4be';ctx.textAlign='center';
    ctx.font='italic bold 35px Georgia';ctx.fillText('la marzocco',w/2,45);
    ctx.font='18px Arial';ctx.fillText('HOME',w/2,72);
  },384,96);
  mesh(new THREE.PlaneGeometry(.36,.09),new THREE.MeshBasicMaterial({map:scaleBrand,transparent:true,depthWrite:false}),machine,[.28,.875,2.544]);
  const logo = texture((ctx,w,h)=>{
    ctx.clearRect(0,0,w,h);ctx.fillStyle='#a41220';ctx.font='900 96px Arial Black, Arial';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('LA MARZOCCO',w/2,h/2);
  },1024,128);
  mesh(new THREE.PlaneGeometry(1.43,0.18),new THREE.MeshBasicMaterial({map:logo,transparent:true,depthWrite:false}),machine,[0.77,0.43,2.675]);

  // Cups and a small wooden-handled tool on the warming deck.
  function cup(x,z,y,radius=0.28) {
    const shape=[[0,0],[radius*.7,0],[radius*.82,.08],[radius,.4],[radius,.43],[radius-.035,.43],[radius-.04,.12],[0,.12]];
    mesh(new THREE.LatheGeometry(shape.map(p=>new THREE.Vector2(...p)),40),mat.ceramic,deck,[x,y,z],'white-cup');
    const ring=mesh(new THREE.TorusGeometry(.14,.032,10,32),mat.ceramic,deck,[x+radius+.09,y+.24,z]);ring.rotation.y=Math.PI/2;
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
  cylinder(.31,.73,[-.79,1.07,-.9],mat.black,internals,'z','pump-motor');
  cylinder(.22,.24,[-.79,1.07,-.42],mat.brass,internals,'z');
  tube([[-.79,1.07,-.25],[-.79,1.25,.5],[-.35,2.16,.67],[0,2.4,1.02]],.038,mat.copper,internals);
  tube([[.95,2.4,-.75],[1.35,2.6,-.5],[1.36,2.74,.8],[1.25,2.5,1.76]],.043,mat.copper,internals);
  tube([[0,2.72,1.02],[0,2.77,1.6],[0,2.5,1.89]],.05,mat.copper,internals);
  box([.62,.62,.33],[.82,1.04,-1.13],mat.black,internals);

  const floor=mesh(new THREE.PlaneGeometry(18,18),new THREE.ShadowMaterial({opacity:.3}),scene,[0,.09,0]);
  floor.rotation.x=-Math.PI/2;floor.castShadow=false;
  for(const radius of [3.5,4.1]) {
    const ring=mesh(new THREE.RingGeometry(radius,radius+.01,120),new THREE.MeshBasicMaterial({color:0x547473,transparent:true,opacity:.17,side:THREE.DoubleSide,depthWrite:false}),scene,[0,.08,0]);
    ring.rotation.x=-Math.PI/2;ring.castShadow=false;
  }
  const anchors={boiler:new THREE.Vector3(-.08,2.75,1.2),group:new THREE.Vector3(0,2.16,2.1),scale:new THREE.Vector3(0,.98,2.22)};
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
      element.hidden=project.z>1||x<0||x>viewport.clientWidth||y<0||y>viewport.clientHeight||state.mode==='exploded';
    }
  }
  function request() { if(!frame && state.visible && !document.hidden && !state.contextLost)frame=requestAnimationFrame(render); }
  function render(time) {
    frame=0;
    const dt=Math.min((time-lastTime)/1000 || .016,.05);lastTime=time;
    let moving=false;
    for(const part of panels) {
      const target=part.base.clone();
      if(state.mode==='exploded')target.add(part.offset);
      if(part.object.position.distanceTo(target)>.001) {part.object.position.lerp(target,reduced.matches?1:1-Math.exp(-dt*9));moving=true;}
      part.object.visible=!(state.mode==='cutaway'&&part.hideInside);
    }
    fascia.visible=state.mode!=='cutaway';
    controls.update(dt);hotspots();renderer.render(scene,camera);
    if(moving||dragging||controls.autoRotate||damping-->0)request();
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
  new IntersectionObserver(entries=>{state.visible=entries[0].isIntersecting;if(state.visible){resize();request();}}).observe(viewport);
  document.addEventListener('visibilitychange',()=>{lastTime=0;request();});
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
      let object=hit.object;while(object&&!object.userData.component)object=object.parent;
      if(object){onSelect(object.userData.component);break;}
    }
  });
  function mode(value) {
    const wasExploded=state.mode==='exploded';
    const offset=camera.position.clone().sub(controls.target);
    if(value==='exploded'&&!wasExploded)offset.multiplyScalar(1.2);
    if(value!=='exploded'&&wasExploded)offset.divideScalar(1.2);
    state.mode=value;
    document.querySelectorAll('[data-mode]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.mode===value)));
    document.getElementById('model-hint').textContent=value==='assembled'?'DRAG TO ORBIT · SELECT A COMPONENT':'INTERNAL LAYOUT IS SCHEMATIC · DRAG TO EXPLORE';
    if(value==='exploded'){controls.target.set(0,2.5,0);}
    else{controls.target.set(0,2.25,.1);}
    camera.position.copy(controls.target).add(offset);
    request();
  }
  document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>mode(button.dataset.mode)));
  document.querySelectorAll('[data-camera]').forEach(button=>button.addEventListener('click',()=>{
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
  return {
    mode,resize,
    update(data){mat.red.emissiveIntensity=data.status?.power_on?2:0;mat.blue.emissiveIntensity=data.status?.power_on?2:0;request();},
    diagnostics(){return {mode:state.mode,interactive:state.interactive,visible:state.visible,contextLost:state.contextLost,autoRotate:controls.autoRotate,camera:camera.position.toArray(),gauges:2,woodenControls:2,cups:3,triangles:renderer.info.render.triangles,renderCalls:renderer.info.render.calls};},
  };
}
