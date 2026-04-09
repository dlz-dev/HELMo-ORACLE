/* ── Oracle Doc Viewer ─────────────────────────────────────────────────── */
/* Lit le contenu pré-embarqué depuis DOCS_CONTENT (doc-content.js).
   Pas de fetch() — fonctionne sur tout hébergement statique (Vercel, etc.) */

(function () {
  'use strict';

  /* ── MERMAID CONFIG ───────────────────────────────────────────────────── */
  if (typeof mermaid !== 'undefined') {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      themeVariables: {
        background:          '#0d0f14',
        primaryColor:        '#1a1d26',
        primaryTextColor:    '#f0f2f5',
        primaryBorderColor:  'rgba(201,168,76,0.5)',
        lineColor:           '#C9A84C',
        secondaryColor:      '#12141e',
        tertiaryColor:       '#0d0f14',
        edgeLabelBackground: '#12141e',
        clusterBkg:          '#12141e',
        titleColor:          '#C9A84C',
        nodeBorder:          'rgba(201,168,76,0.4)',
        mainBkg:             '#1a1d26',
        nodeTextColor:       '#f0f2f5',
        labelTextColor:      '#f0f2f5',
        actorBkg:            '#1a1d26',
        actorBorder:         'rgba(201,168,76,0.4)',
        actorTextColor:      '#f0f2f5',
        signalColor:         '#C9A84C',
        signalTextColor:     '#f0f2f5',
        fontFamily:          'Plus Jakarta Sans, sans-serif',
        fontSize:            '13px',
      },
      flowchart: { curve: 'basis', htmlLabels: true },
      securityLevel: 'loose',
    });
  }

  /* ── MARKED CONFIG (v4 API — strings) ─────────────────────────────────── */
  const renderer = new marked.Renderer();

  renderer.heading = function (text, level) {
    const id = text
      .replace(/<[^>]+>/g, '')
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/\s+/g, '-');
    return `<h${level} id="${id}">${text}</h${level}>\n`;
  };

  /* Blocs de code : mermaid → div.mermaid, reste → Prism */
  renderer.code = function (code, lang) {
    const language = (lang || '').split(' ')[0].toLowerCase();

    /* Mermaid : on rend juste un conteneur, pas de Prism */
    if (language === 'mermaid') {
      return `<div class="mermaid-wrap"><div class="mermaid">${escapeHtml(code)}</div></div>`;
    }

    const prismLang = Prism.languages[language] ? language : 'text';
    const highlighted = Prism.highlight(
      code,
      Prism.languages[prismLang] || Prism.languages.text,
      prismLang
    );
    /* Pas de ::before ni de barre blanche : le bouton Copier est en bas à droite */
    return `<div class="code-block-wrap">
<pre class="language-${prismLang}"><code class="language-${prismLang}">${highlighted}</code></pre>
<button class="copy-btn" onclick="copyCode(this)" aria-label="Copier">
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
  Copier
</button>
</div>`;
  };

  renderer.blockquote = function (quote) {
    const inner = quote.replace(/<[^>]+>/g, '').trim();
    let cls = '', badge = '';
    if (/^(⚠️|WARNING|ATTENTION)/i.test(inner)) {
      cls = 'alert-warning';
      badge = '<span class="alert-badge" style="background:rgba(245,158,11,0.12);color:#fbbf24;">⚠ Attention</span>';
    } else if (/^(❌|DANGER|ERROR)/i.test(inner)) {
      cls = 'alert-danger';
      badge = '<span class="alert-badge" style="background:rgba(239,68,68,0.12);color:#f87171;">✕ Danger</span>';
    } else if (/^(✅|INFO|NOTE)/i.test(inner)) {
      cls = 'alert-info';
      badge = '<span class="alert-badge" style="background:rgba(59,130,246,0.12);color:#93c5fd;">ℹ Info</span>';
    }
    return `<blockquote class="${cls}">${badge}${quote}</blockquote>\n`;
  };

  marked.setOptions({ gfm: true, breaks: false, renderer });

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  /* ── COPY HELPER (global) ─────────────────────────────────────────────── */
  window.copyCode = function (btn) {
    const code = btn.closest('.code-block-wrap').querySelector('code').innerText;
    navigator.clipboard.writeText(code).then(() => {
      btn.textContent = 'Copié !';
      setTimeout(() => {
        btn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copier`;
      }, 1500);
    });
  };

  /* ── TOC ──────────────────────────────────────────────────────────────── */
  function buildTOC(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    const headings = tmp.querySelectorAll('h2, h3');
    const tocList    = document.getElementById('toc-list');
    const tocSection = document.getElementById('toc-section');
    tocList.innerHTML = '';

    if (headings.length < 2) { tocSection.style.display = 'none'; return; }
    tocSection.style.display = 'block';
    headings.forEach(h => {
      const li = document.createElement('li');
      const a  = document.createElement('a');
      a.href = '#' + h.id;
      a.className = 'sidebar-link';
      a.style.paddingLeft = h.tagName === 'H3' ? '36px' : '28px';
      a.style.fontSize    = h.tagName === 'H3' ? '11px' : '12px';
      a.style.color       = h.tagName === 'H3' ? 'rgba(240,242,245,0.4)' : '';
      a.textContent = h.textContent;
      a.addEventListener('click', e => {
        e.preventDefault();
        document.getElementById(h.id)?.scrollIntoView({ behavior: 'smooth' });
      });
      li.appendChild(a);
      tocList.appendChild(li);
    });
  }

  /* ── MERMAID RENDER ───────────────────────────────────────────────────── */
  function renderMermaid(container) {
    if (typeof mermaid === 'undefined') return;
    const diagrams = container.querySelectorAll('.mermaid');
    if (!diagrams.length) return;
    /* mermaid v10 async API */
    mermaid.run({ nodes: diagrams }).catch(() => {
      /* fallback : show raw source in a styled pre */
      diagrams.forEach(d => {
        const pre = document.createElement('pre');
        pre.style.cssText = 'background:#0d0f14;border:1px solid rgba(201,168,76,0.2);border-radius:8px;padding:16px;color:rgba(240,242,245,0.5);font-size:12px;overflow-x:auto';
        pre.textContent = d.textContent;
        d.parentNode.replaceChild(pre, d);
      });
    });
  }

  /* ── RENDER DOC ───────────────────────────────────────────────────────── */
  function renderDoc(key) {
    const contentArea = document.getElementById('docs-content');
    const mdBody      = document.getElementById('md-body');

    contentArea.style.display = 'block';

    const md = (typeof DOCS_CONTENT !== 'undefined' && DOCS_CONTENT[key])
      ? DOCS_CONTENT[key]
      : `# Document introuvable\n\nLa clé \`${key}\` n'existe pas dans DOCS_CONTENT.`;

    const html = marked.parse(md);
    mdBody.innerHTML = html;
    buildTOC(html);
    Prism.highlightAllUnder(mdBody);
    renderMermaid(mdBody);

    /* Fade-in */
    contentArea.style.animation = 'none';
    void contentArea.offsetWidth;
    contentArea.style.animation = '';

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /* ── SIDEBAR NAV ──────────────────────────────────────────────────────── */
  function initNav() {
    const links = document.querySelectorAll('.sidebar-link[data-doc]');
    links.forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        links.forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        renderDoc(link.dataset.doc);
      });
    });
  }

  /* ── INJECT STYLES ────────────────────────────────────────────────────── */
  function injectStyles() {
    const s = document.createElement('style');
    s.textContent = `
      /* ── Code block : pas de pseudo-element navbar, bouton en bas ── */
      #md-body pre::before { display: none !important; }

      .code-block-wrap { position: relative; margin: 20px 0; }

      .copy-btn {
        position: absolute;
        bottom: 10px; right: 10px;        /* ← en BAS à droite, pas en haut */
        background: rgba(8,10,15,0.7);
        border: 1px solid rgba(255,255,255,0.08);
        color: rgba(240,242,245,0.35);
        font-size: 11px;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 600;
        padding: 3px 9px;
        border-radius: 5px;
        cursor: pointer;
        display: flex; align-items: center; gap: 4px;
        transition: color .2s, border-color .2s, background .2s;
        line-height: 1.6;
      }
      .copy-btn:hover {
        background: rgba(201,168,76,0.08);
        color: #C9A84C;
        border-color: rgba(201,168,76,0.3);
      }

      /* ── Mermaid wrapper ── */
      .mermaid-wrap {
        margin: 24px 0;
        background: rgba(10,12,18,0.7);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px;
        padding: 20px;
        overflow-x: auto;
      }
      .mermaid-wrap svg {
        max-width: 100%;
        height: auto;
        display: block;
        margin: 0 auto;
      }
      /* Force mermaid dark text colors */
      .mermaid-wrap .label { color: #f0f2f5 !important; }
      .mermaid-wrap .edgeLabel { background: #12141e !important; color: #f0f2f5 !important; }
    `;
    document.head.appendChild(s);
  }

  /* ── INIT ─────────────────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', () => {
    injectStyles();
    initNav();
    renderDoc('readme');
  });

})();
