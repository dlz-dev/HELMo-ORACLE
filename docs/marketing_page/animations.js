/**
 * animations.js v7 — Oracle
 * Warp/Starfield Three.js + Apple Bento White Mode
 */

document.addEventListener('DOMContentLoaded', () => {
  // Init Three.js background
  let bg = null;
  try {
    if (typeof THREE !== 'undefined') {
      bg = new OracleBackground();
    } else {
      console.warn('Three.js not found, skipping 3D background.');
    }
  } catch (e) {
    console.warn('Background init failed:', e);
  }

  // Smooth scroll
  const lenis = initLenis();

  // UI
  initHeader();
  initIO();
  initJudgeIO();

  // GSAP
  if (typeof gsap !== 'undefined') {
    if (typeof ScrollTrigger !== 'undefined') {
      gsap.registerPlugin(ScrollTrigger);
      initGSAP();
    }
    initHeroEntrance();
  }

  // Warp button
  initWarpButton(bg);
});

/* ─────────────────────────────────────────────────────────────────────────
   THREE.JS BACKGROUND — Sphere of particles
───────────────────────────────────────────────────────────────────────── */
class OracleBackground {
  constructor() {
    this.container = document.getElementById('canvas-container');
    if (!this.container) return;

    // Use container dimensions (not window) to avoid oval sphere
    const w = this.container.clientWidth  || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;

    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(70, w / h, 0.1, 5000);
    this.camera.position.z = 520;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x000000, 0);
    this.container.appendChild(this.renderer.domElement);

    this.particleCount = 5000;
    this.colorGold = new THREE.Color(0xC9A84C);
    this.colorWhite = new THREE.Color(0xffffff);

    // Sphere radius and particle positions
    this.sphereRadius = 220;
    this.basePositions = null;

    this.group = new THREE.Group();
    this.scene.add(this.group);

    this._buildParticles();
    this._introAnimation();

    window.addEventListener('resize', () => this._onResize());
    this._animate();
  }

  _buildParticles() {
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array(this.particleCount * 3);
    const col = new Float32Array(this.particleCount * 3);
    const sizes = new Float32Array(this.particleCount);

    this.basePositions = pos.slice(); // keep original for warp restoration

    for (let i = 0; i < this.particleCount; i++) {
      // Distribute uniformly on sphere surface
      const u = Math.random();
      const v = Math.random();
      const theta = 2 * Math.PI * u;
      const phi = Math.acos(2 * v - 1);
      const r = this.sphereRadius * (0.85 + Math.random() * 0.3);

      pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      pos[i * 3 + 2] = r * Math.cos(phi);

      // Mix gold and white
      const mix = Math.random();
      const c = this.colorGold.clone().lerp(this.colorWhite, mix * 0.4);
      col[i * 3]     = c.r;
      col[i * 3 + 1] = c.g;
      col[i * 3 + 2] = c.b;

      sizes[i] = 1.5 + Math.random() * 2.5;
    }

    this.basePositions = pos.slice();

    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color',    new THREE.BufferAttribute(col, 3));
    geo.setAttribute('size',     new THREE.BufferAttribute(sizes, 1));

    const mat = new THREE.PointsMaterial({
      size: 2.2,
      vertexColors: true,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      sizeAttenuation: true,
    });

    this.particles = new THREE.Points(geo, mat);
    this.group.add(this.particles);
  }

  _introAnimation() {
    if (typeof gsap === 'undefined') return;
    this.camera.position.z = 1400;
    gsap.to(this.camera.position, {
      z: 520, duration: 2.8, ease: 'expo.out', delay: 0.3
    });
    gsap.from(this.particles.material, {
      opacity: 0, duration: 2, delay: 0.3, ease: 'power2.out'
    });
  }

  _onResize() {
    if (!this.camera || !this.renderer || !this.container) return;
    const w = this.container.clientWidth  || window.innerWidth;
    const h = this.container.clientHeight || window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  }

  _animate() {
    requestAnimationFrame(() => this._animate());
    if (this.group) {
      this.group.rotation.y += 0.0008;
      this.group.rotation.x += 0.0003;
    }
    this.renderer.render(this.scene, this.camera);
  }

  /**
   * WARP EFFECT: camera rushes through the particle sphere then comes back
   * @param {Function} onComplete - called when warp is fully done
   */
  warp(onComplete) {
    if (typeof gsap === 'undefined') {
      if (onComplete) onComplete();
      return;
    }

    const tl = gsap.timeline({
      onComplete: () => { if (onComplete) onComplete(); }
    });

    // Phase 1 — Rush THROUGH the sphere (warp speed)
    tl.to(this.camera.position, {
      z: -600,
      duration: 1.9,
      ease: 'expo.in',
    }, 0);

    // Rotate particles fast during warp-in
    tl.to(this.group.rotation, {
      y: this.group.rotation.y + Math.PI * 6,
      duration: 1.9,
      ease: 'expo.in',
    }, 0);

    // Stretch particles to create warp streaks
    tl.to(this.particles.material, {
      size: 12,
      opacity: 1,
      duration: 1.9,
      ease: 'expo.in',
    }, 0);

    // Phase 2 — Reverse: sphere reforms
    tl.to(this.camera.position, {
      z: 520,
      duration: 1.8,
      ease: 'expo.out',
    }, 1.9);

    tl.to(this.particles.material, {
      size: 2.2,
      opacity: 0.75,
      duration: 1.8,
      ease: 'expo.out',
    }, 1.9);
  }

  // Fade canvas opacity based on scroll position
  setOpacity(opacity) {
    if (!this.renderer) return;
    gsap.to(this.renderer.domElement, { opacity, duration: 0.6 });
  }
}

/* ─────────────────────────────────────────────────────────────────────────
   WARP BUTTON
───────────────────────────────────────────────────────────────────────── */
function initWarpButton(bg) {
  const btn = document.getElementById('warp-btn');
  if (!btn) return;

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    const dest = btn.getAttribute('href') || 'https://oracle.dlzteam.com/';

    if (!bg) {
      window.open(dest, '_blank');
      return;
    }

    // 1 — Hide hero content
    const heroContent = document.getElementById('hero-content');
    if (heroContent && typeof gsap !== 'undefined') {
      gsap.to(heroContent, { opacity: 0, scale: 0.96, duration: 0.45, ease: 'power2.in' });
    }

    // 2 — Trigger warp
    bg.warp(() => {
      // 3 — Restore hero content
      if (heroContent && typeof gsap !== 'undefined') {
        gsap.to(heroContent, { opacity: 1, scale: 1, duration: 0.6, ease: 'power2.out' });
      }
      // Navigate in background after the wow moment
      setTimeout(() => { window.open(dest, '_blank'); }, 400);
    });
  });
}

/* ─────────────────────────────────────────────────────────────────────────
   GSAP — Scroll triggers
───────────────────────────────────────────────────────────────────────── */
function initGSAP() {
  // Nothing complex needed — white mode is default
  // We just fade canvas out once user scrolls past hero
}

function initHeroEntrance() {
  const items = ['#hero-badge', '#hero-title', '#hero-sub', '#hero-sub2', '#hero-ctas', '#hero-bento'];
  const existing = items.filter(id => document.querySelector(id));
  if (!existing.length) return;

  gsap.fromTo(existing,
    { opacity: 0, y: 32 },
    { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out', stagger: 0.1, delay: 0.4 }
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   SCROLL — Native only (Lenis removed: caused visible lag)
───────────────────────────────────────────────────────────────────────── */
function initLenis() {
  // Lenis disabled — native scroll is smooth enough and avoids double-proxy lag
  return null;
}

/* ─────────────────────────────────────────────────────────────────────────
   HEADER — Scroll state
───────────────────────────────────────────────────────────────────────── */
function initHeader() {
  const h = document.getElementById('site-header');
  if (!h) return;

  const hero = document.getElementById('hero');
  const canvas = document.getElementById('canvas-container');

  window.addEventListener('scroll', () => {
    const heroHeight = hero ? hero.offsetHeight : window.innerHeight;
    const scrolled = window.scrollY > 60;
    h.classList.toggle('scrolled', scrolled);

    // Switch header style once past hero
    document.body.classList.toggle('page-scrolled', window.scrollY > heroHeight - 100);

    // Canvas is inside hero — no need to hide it manually, it scrolls away naturally
  }, { passive: true });
}

/* ─────────────────────────────────────────────────────────────────────────
   INTERSECTION OBSERVER — Reveal animations
───────────────────────────────────────────────────────────────────────── */
function initIO() {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.classList.add('visible');
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
}

/* ─────────────────────────────────────────────────────────────────────────
   LLM JUDGE BARS
───────────────────────────────────────────────────────────────────────── */
function initJudgeIO() {
  const panel = document.getElementById('judge-metrics');
  if (!panel) return;

  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        animateJudgeBars();
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.2 });

  obs.observe(panel);
}

function animateJudgeBars() {
  document.querySelectorAll('#judge-metrics .judge-metric-full').forEach((m, i) => {
    const pct = m.dataset.pct;
    const score = parseFloat(m.dataset.score);
    const fill = m.querySelector('.metric-bar-fill');
    const scoreEl = m.querySelector('.metric-score');
    if (!fill || !scoreEl) return;

    setTimeout(() => {
      fill.style.width = pct + '%';
      const start = Date.now(), dur = 800;
      const tick = () => {
        const t = Math.min((Date.now() - start) / dur, 1);
        const eased = 1 - Math.pow(1 - t, 3);
        scoreEl.textContent = (score * eased).toFixed(1);
        if (t < 1) requestAnimationFrame(tick);
        else scoreEl.textContent = score.toFixed(1) + ' / 5';
      };
      requestAnimationFrame(tick);
    }, i * 150);
  });
}
