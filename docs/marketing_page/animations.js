/**
 * animations.js v4 — Oracle
 * GSAP + ScrollTrigger + Lenis already loaded in <head>
 * No dynamic script loading — eliminates cascade delay
 */

document.addEventListener('DOMContentLoaded', () => {
  initLenis();
  initIO();
  initHeader();
  initSphereParallax();
  initJudgeIO();
  if (typeof gsap !== 'undefined') initGSAP();
});

function initLenis() {
  if (typeof Lenis === 'undefined') return;
  const lenis = new Lenis({
    duration: 0.9,
    easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
    wheelMultiplier: 1.0,
  });
  const raf = time => { lenis.raf(time); requestAnimationFrame(raf); };
  requestAnimationFrame(raf);
  if (typeof ScrollTrigger !== 'undefined') lenis.on('scroll', ScrollTrigger.update);
}

function initIO() {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        e.target.style.willChange = 'opacity, transform';
        e.target.classList.add('visible');
        setTimeout(() => { e.target.style.willChange = 'auto'; }, 800);
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -50px 0px' });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
}

function initHeader() {
  const h = document.getElementById('site-header');
  if (!h) return;
  let lastScroll = 0;
  window.addEventListener('scroll', () => {
    const now = scrollY;
    if (Math.abs(now - lastScroll) < 10) return;
    h.classList.toggle('scrolled', now > 60);
    lastScroll = now;
  }, { passive: true });
}

function initSphereParallax() {
  const sphere = document.getElementById('sphere');
  if (!sphere) return;
  let mouseX = 0, mouseY = 0, curX = 0, curY = 0;
  let active = false;
  document.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 14;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 10;
    if(!active) { active = true; requestAnimationFrame(animate); }
  }, { passive: true });
  const animate = () => {
    const dx = mouseX - curX;
    const dy = mouseY - curY;
    if (Math.abs(dx) < 0.01 && Math.abs(dy) < 0.01) { active = false; return; }
    curX += dx * 0.08;
    curY += dy * 0.08;
    sphere.style.transform = `translateY(0) rotateX(${-curY}deg) rotateY(${curX}deg)`;
    requestAnimationFrame(animate);
  };
}

function initJudgeIO() {
  const panel = document.getElementById('judge-metrics');
  if (!panel) return;
  let fired = false;
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting && !fired) { fired = true; animateJudgeBars(); obs.unobserve(e.target); }
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
    setTimeout(() => {
      if (fill) fill.style.width = pct + '%';
      if (scoreEl) {
        const start = Date.now(), dur = 750;
        const tick = () => {
          const t = Math.min((Date.now() - start) / dur, 1);
          const ease = 1 - Math.pow(1 - t, 3);
          scoreEl.textContent = (score * ease).toFixed(1);
          if (t < 1) requestAnimationFrame(tick);
          else scoreEl.textContent = score.toFixed(1) + ' / 5';
        };
        requestAnimationFrame(tick);
      }
    }, i * 140);
  });
}

function initGSAP() {
  gsap.registerPlugin(ScrollTrigger);

  // Hero entrance
  gsap.fromTo(
    ['#hero-badge', '#hero-title', '#hero-sub', '#hero-ctas', '#hero-visual'],
    { opacity: 0, y: 30 },
    { opacity: 1, y: 0, duration: 0.7, ease: 'power2.out', stagger: 0.08, delay: 0.05 }
  );

  // Orbs parallax - much more responsive scrub
  document.querySelectorAll('.orb').forEach((orb, i) => {
    gsap.to(orb, {
      y: i % 2 === 0 ? -60 : 60, ease: 'none',
      scrollTrigger: { trigger: 'body', start: 'top top', end: 'bottom bottom', scrub: 0.8 + i * 0.2 }
    });
  });

  // Shield
  const shield = document.getElementById('shield-wrap');
  if (shield) {
    gsap.fromTo(shield, { opacity: 0, scale: 0.9 },
      { opacity: 1, scale: 1, duration: 0.8, ease: 'power2.out',
        scrollTrigger: { trigger: '#sovereign', start: 'top 75%', once: true } });
    gsap.fromTo('.flow-line', { opacity: 0 },
      { opacity: 0.7, duration: 0.5, stagger: 0.08,
        scrollTrigger: { trigger: '#sovereign', start: 'top 65%', once: true } });
  }

  // Ultra float on scroll
  const ultra = document.getElementById('ultra-card');
  if (ultra) {
    gsap.to(ultra, {
      y: -15, ease: 'none',
      scrollTrigger: { trigger: '#pricing', start: 'top bottom', end: 'bottom top', scrub: 0.6 }
    });
  }

  // Pricing entrance
  gsap.fromTo('.pricing-card',
    { opacity: 0, y: 35 },
    { opacity: 1, y: 0, duration: 0.6, stagger: 0.06, ease: 'power2.out',
      scrollTrigger: { trigger: '#pricing', start: 'top 75%', once: true } }
  );
}
