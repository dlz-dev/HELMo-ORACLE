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
    duration: 1.1,
    easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
    wheelMultiplier: 0.85,
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
        setTimeout(() => { e.target.style.willChange = 'auto'; }, 700);
        obs.unobserve(e.target);
      }
    });
  }, { threshold: 0.10, rootMargin: '0px 0px -30px 0px' });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
}

function initHeader() {
  const h = document.getElementById('site-header');
  if (!h) return;
  window.addEventListener('scroll', () => h.classList.toggle('scrolled', scrollY > 60), { passive: true });
}

function initSphereParallax() {
  const sphere = document.getElementById('sphere');
  if (!sphere) return;
  let mouseX = 0, mouseY = 0, curX = 0, curY = 0;
  document.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 14;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 10;
  }, { passive: true });
  const animate = () => {
    curX += (mouseX - curX) * 0.06;
    curY += (mouseY - curY) * 0.06;
    sphere.style.transform = `translateY(0) rotateX(${-curY}deg) rotateY(${curX}deg)`;
    requestAnimationFrame(animate);
  };
  animate();
}

function initJudgeIO() {
  const panel = document.getElementById('judge-metrics');
  if (!panel) return;
  let fired = false;
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
      if (e.isIntersecting && !fired) { fired = true; animateJudgeBars(); obs.unobserve(e.target); }
    });
  }, { threshold: 0.3 });
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
        const start = Date.now(), dur = 800;
        const tick = () => {
          const t = Math.min((Date.now() - start) / dur, 1);
          const ease = 1 - Math.pow(1 - t, 3);
          scoreEl.textContent = (score * ease).toFixed(1);
          if (t < 1) requestAnimationFrame(tick);
          else scoreEl.textContent = score.toFixed(1) + ' / 5';
        };
        requestAnimationFrame(tick);
      }
    }, i * 160);
  });
}

function initGSAP() {
  gsap.registerPlugin(ScrollTrigger);

  // Hero entrance
  gsap.fromTo(
    ['#hero-badge', '#hero-title', '#hero-sub', '#hero-ctas', '#hero-visual'],
    { opacity: 0, y: 32 },
    { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out', stagger: 0.1, delay: 0.1 }
  );

  // Orbs parallax
  document.querySelectorAll('.orb').forEach((orb, i) => {
    gsap.to(orb, {
      y: i % 2 === 0 ? -80 : 80, ease: 'none',
      scrollTrigger: { trigger: 'body', start: 'top top', end: 'bottom bottom', scrub: 2.5 + i * 0.3 }
    });
  });

  // Shield
  const shield = document.getElementById('shield-wrap');
  if (shield) {
    gsap.fromTo(shield, { opacity: 0, scale: 0.85 },
      { opacity: 1, scale: 1, duration: 1, ease: 'power3.out',
        scrollTrigger: { trigger: '#sovereign', start: 'top 68%', once: true } });
    gsap.fromTo('.flow-line', { opacity: 0 },
      { opacity: 0.7, duration: 0.6, stagger: 0.1,
        scrollTrigger: { trigger: '#sovereign', start: 'top 58%', once: true } });
  }

  // Ultra float on scroll
  const ultra = document.getElementById('ultra-card');
  if (ultra) {
    gsap.to(ultra, {
      y: -18, ease: 'none',
      scrollTrigger: { trigger: '#pricing', start: 'top bottom', end: 'bottom top', scrub: 1.2 }
    });
  }

  // Pricing entrance
  gsap.fromTo('.pricing-card',
    { opacity: 0, y: 40 },
    { opacity: 1, y: 0, duration: 0.7, stagger: 0.08, ease: 'power2.out',
      scrollTrigger: { trigger: '#pricing', start: 'top 68%', once: true } }
  );
}
