// Papo Dado Blog: funções usadas pela página inicial, pela lista do blog, pelas páginas dos posts e pelo 404.
// Os posts ficam no Supabase; a chave "anon" é pública e só enxerga posts publicados.
(function () {
  const SB = { url: 'https://oumhibikfxorrknthbqb.supabase.co', chave: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im91bWhpYmlrZnhvcnJrbnRoYnFiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMzODcyNDIsImV4cCI6MjEwODk2MzI0Mn0.JlgqDluN1BEHBAGGpbcVw-wVowlcl_x0EjU2E4e-zns' };
  const TZ = 'America/Sao_Paulo';
  const AUTORES = { 'Henrique Müller': '/img/henrique.webp', 'Elisinha Müller': '/img/elisinha.webp' };
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const dataLonga = (iso) => new Intl.DateTimeFormat('pt-BR', { timeZone: TZ, day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(iso));
  const urlPost = (p) => `/blog/${p.slug}/`;

  async function sbGet(caminho) {
    const r = await fetch(`${SB.url}/rest/v1/${caminho}`, { headers: { apikey: SB.chave, Authorization: `Bearer ${SB.chave}` }, cache: 'no-store' });
    if (!r.ok) throw new Error(`Supabase ${r.status}`);
    return r.json();
  }
  const CAMPOS = 'id,slug,titulo,resumo,capa_url,autor,categorias,campanha,publicar_em';
  // { limite, campanha, slug, conteudo }
  async function listar(o = {}) {
    let q = `posts?select=${CAMPOS}${o.conteudo ? ',conteudo' : ''}&order=publicar_em.desc`;
    if (o.campanha) q += `&campanha=eq.${encodeURIComponent(o.campanha)}`;
    if (o.slug) q += `&slug=eq.${encodeURIComponent(o.slug)}`;
    if (o.limite) q += `&limit=${o.limite}`;
    return sbGet(q);
  }

  function assinatura(p) {
    const foto = AUTORES[p.autor];
    return `<span class="assinatura">${foto ? `<img src="${foto}" alt="" width="32" height="32" loading="lazy">` : '<span class="sem-foto" aria-hidden="true"></span>'}
      <span><strong>${esc(p.autor)}</strong> · ${esc(dataLonga(p.publicar_em))}</span></span>`;
  }
  function card(p) {
    return `<a class="post-card" href="${urlPost(p)}" data-cats="${esc((p.categorias || []).join('|'))}">
      <div class="capa">${p.capa_url ? `<img src="${esc(p.capa_url)}" alt="" loading="lazy" width="640" height="360">` : ''}</div>
      <div class="corpo">
        ${p.categorias?.length ? `<div class="cats">${p.categorias.map((c) => `<span class="chip">${esc(c)}</span>`).join('')}</div>` : ''}
        <h3>${esc(p.titulo)}</h3>
        ${p.resumo ? `<p>${esc(p.resumo)}</p>` : ''}
        ${assinatura(p)}
      </div></a>`;
  }

  // Conteúdo vindo do editor: só tags de texto, imagens e vídeos do YouTube (DOMPurify carregado pela página)
  let ganchoPronto = false;
  function limpar(html) {
    if (!window.DOMPurify) return '';
    if (!ganchoPronto) {
      ganchoPronto = true;
      DOMPurify.addHook('uponSanitizeElement', (no, dados) => {
        if (dados.tagName === 'iframe' && !/^https:\/\/www\.youtube(-nocookie)?\.com\/embed\//.test(no.getAttribute('src') || '')) no.remove();
      });
    }
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['p', 'br', 'h2', 'h3', 'strong', 'b', 'em', 'i', 'u', 's', 'a', 'ul', 'ol', 'li', 'blockquote', 'img', 'iframe', 'span', 'hr', 'pre', 'code'],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt', 'width', 'height', 'allowfullscreen', 'frameborder', 'allow', 'title', 'loading'],
    });
  }
  function artigo(p, campanhaNome) {
    return `<article class="post wrap estreito">
      <a class="voltar" href="/blog/">← Todos os posts</a>
      <h1>${esc(p.titulo)}</h1>
      ${p.resumo ? `<p class="linha-fina">${esc(p.resumo)}</p>` : ''}
      <div class="meta">${assinatura(p)}${(p.categorias || []).map((c) => `<a class="chip" href="/blog/?categoria=${encodeURIComponent(c)}">${esc(c)}</a>`).join('')}</div>
      ${p.capa_url ? `<div class="capa-post"><img src="${esc(p.capa_url)}" alt="" width="1200" height="675"></div>` : ''}
      <div class="texto">${limpar(p.conteudo || '')}</div>
      ${p.campanha ? `<div class="campanha-ligada"><span>Este post é sobre <strong>${esc(campanhaNome || p.campanha)}</strong>.</span><a class="btn btn-linha" href="/#/campanha/${encodeURIComponent(p.campanha)}">Ver a campanha</a></div>` : ''}
    </article>`;
  }


  // ================= COMENTÁRIOS =================
  // <section class="comentarios" data-post="<id do post>"> no fim do post. Qualquer leitor comenta só com o nome
  // ou entra com o Google (nome e foto da conta). O admin responde, oculta ou apaga na aba Comentários.
  const GOOGLE_CLIENT_ID = '494149024631-6jpl2pvrsfh0evs9u03i8luea2hrn6aj.apps.googleusercontent.com'; // cliente OAuth "Papo Dado Blog" no Google Cloud; vazio = sem botão do Google
  const CAMPOS_C = 'id,resposta_de,nome,texto,do_autor,avatar_url,criado_em';
  const CORES = ['#00BAFC', '#005DFB', '#7020F9', '#FB0F3A', '#FD7601', '#18A558'];
  const dataCurta = (iso) => new Intl.DateTimeFormat('pt-BR', { timeZone: TZ, day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(iso));
  const dataHora = (iso) => new Intl.DateTimeFormat('pt-BR', { timeZone: TZ, dateStyle: 'long', timeStyle: 'short' }).format(new Date(iso));
  function tempo(iso) {
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return 'agora';
    if (s < 3600) return `há ${Math.floor(s / 60)} min`;
    if (s < 86400) return `há ${Math.floor(s / 3600)} h`;
    if (s < 2 * 86400) return 'ontem';
    if (s < 7 * 86400) return `há ${Math.floor(s / 86400)} dias`;
    return dataCurta(iso);
  }
  const guardado = (k, v) => { try { if (v === undefined) return localStorage.getItem(k) || ''; localStorage.setItem(k, v); } catch { /* sem localStorage */ } return ''; };
  function visitante() {
    let v = guardado('pd_v');
    if (!v) { try { v = crypto.randomUUID(); guardado('pd_v', v); } catch { v = ''; } }
    return v || null;
  }
  function avatar(nome, foto, tam = 40) {
    if (foto) return `<img class="com-avatar" src="${esc(foto)}" alt="" width="${tam}" height="${tam}" loading="lazy" referrerpolicy="no-referrer">`;
    const n = String(nome || '?').trim();
    let h = 0; for (const c of n.toLowerCase()) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return `<span class="com-avatar" style="background:${CORES[h % CORES.length]}" aria-hidden="true">${esc(n.charAt(0).toUpperCase() || '?')}</span>`;
  }
  const carregarScript = (src) => new Promise((ok, falha) => {
    const s = document.createElement('script'); s.src = src; s.async = true; s.onload = ok; s.onerror = falha; document.head.appendChild(s);
  });
  let leitorSb = null;
  async function leitor() {
    if (leitorSb) return leitorSb;
    if (!window.supabase) await carregarScript('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.min.js');
    leitorSb = window.supabase.createClient(SB.url, SB.chave, { auth: { storageKey: 'pd-leitor', persistSession: true, autoRefreshToken: true, detectSessionInUrl: false } });
    return leitorSb;
  }
  function caixaComentarios(postId) {
    return `<section class="comentarios wrap estreito" id="comentarios" data-post="${esc(postId)}" aria-labelledby="com-titulo"></section>`;
  }
  function umComentario(c, respostas) {
    const quem = `<strong>${esc(c.nome)}</strong>${c.do_autor ? ' <span class="selo-autor">Autor</span>' : ''}`;
    const corpo = esc(c.texto).split(/\n{2,}/).map((t) => `<p>${t.replace(/\n/g, '<br>')}</p>`).join('');
    return `<li class="comentario${c.do_autor ? ' do-autor' : ''}" id="c-${esc(c.id)}">
      ${avatar(c.nome, c.avatar_url || (c.do_autor && AUTORES[c.nome]))}
      <div class="com-corpo">
        <div class="com-cab">${quem}<time class="com-data" datetime="${esc(c.criado_em)}" title="${esc(dataHora(c.criado_em))}">${esc(tempo(c.criado_em))}</time></div>
        <div class="com-texto">${corpo}</div>
        ${respostas ? `<button type="button" class="com-responder" data-responder="${esc(c.id)}" data-nome="${esc(c.nome)}">Responder</button>` : ''}
        ${respostas && respostas.length ? `<ol class="respostas">${respostas.map((r) => umComentario(r, null)).join('')}</ol>` : ''}
      </div>
    </li>`;
  }
  const ICONE = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm3 5v2h2V9H7zm4 0v2h2V9h-2zm4 0v2h2V9h-2z"/></svg>';
  async function comentarios() {
    const caixa = document.getElementById('comentarios');
    if (!caixa || !caixa.dataset.post) return;
    const postId = caixa.dataset.post;
    caixa.innerHTML = `<div class="com-topo"><span class="com-icone">${ICONE}</span><div><div class="rotulo">Comentários</div>
        <h2 id="com-titulo">Puxe uma cadeira e comente</h2></div></div>
      <ol class="lista-com" id="lista-com"><li class="com-vazio">Carregando os comentários…</li></ol>
      <form class="form-com" id="form-com" novalidate>
        <h3 class="form-titulo">Deixe seu comentário</h3>
        <div class="com-conta" id="com-conta"></div>
        <p class="respondendo" id="respondendo" hidden><span></span> <button type="button" id="cancelar-resposta">Cancelar</button></p>
        <label id="campo-nome"><span>Seu nome</span><input id="com-nome" maxlength="60" autocomplete="name" placeholder="Como quer aparecer na conversa" required></label>
        <label><span>Seu comentário</span><textarea id="com-texto" rows="4" maxlength="2000" required placeholder="O que você achou? Já aconteceu algo parecido na sua mesa?"></textarea></label>
        <label class="isca" aria-hidden="true">Site<input id="com-site" tabindex="-1" autocomplete="off"></label>
        <div class="com-acoes"><button class="btn btn-play" type="submit">Publicar comentário</button><span class="com-msg" id="com-msg" role="status"></span></div>
        <p class="com-regras">Aqui é mesa de amigos: seja gentil. Comentários ofensivos ou spam são removidos. Não pedimos seu e-mail. <a href="/privacidade">Privacidade</a></p>
      </form>`;
    const $c = (s) => caixa.querySelector(s);
    const lista = $c('#lista-com'), form = $c('#form-com'), msg = $c('#com-msg'), conta = $c('#com-conta');
    const nome = $c('#com-nome'), texto = $c('#com-texto'), aviso = $c('#respondendo'), campoNome = $c('#campo-nome');
    nome.value = guardado('pd_nome');
    let respondendo = null, sessao = null;

    const responderA = (id, quem) => {
      respondendo = id; aviso.hidden = !id;
      if (id) { aviso.querySelector('span').textContent = `Respondendo a ${quem}`; texto.focus(); }
    };
    function mostrarConta() {
      const u = sessao?.user;
      campoNome.hidden = !!u;
      if (u) {
        const m = u.user_metadata || {};
        const n = m.full_name || m.name || u.email;
        conta.innerHTML = `<div class="com-logado">${avatar(n, m.avatar_url || m.picture, 32)}<span>Comentando como <strong>${esc(n)}</strong></span><button type="button" id="com-sair">Sair</button></div>`;
        conta.querySelector('#com-sair').addEventListener('click', async () => { (await leitor()).auth.signOut(); sessao = null; mostrarConta(); });
      } else if (GOOGLE_CLIENT_ID) {
        conta.innerHTML = '<div class="com-google"><span>Entre com o Google para comentar com seu nome e foto, ou só escreva seu nome abaixo.</span><div id="com-gbtn"></div></div>';
        botaoGoogle();
      } else conta.innerHTML = '';
    }
    async function botaoGoogle() {
      try {
        if (!window.google?.accounts?.id) await carregarScript('https://accounts.google.com/gsi/client');
        google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID, ux_mode: 'popup', use_fedcm_for_prompt: true,
          callback: async ({ credential }) => {
            msg.textContent = 'Entrando…';
            const { data, error } = await (await leitor()).auth.signInWithIdToken({ provider: 'google', token: credential });
            msg.textContent = error ? 'Não consegui entrar com o Google. Tente de novo.' : '';
            if (!error) { sessao = data.session; mostrarConta(); }
          },
        });
        const alvo = conta.querySelector('#com-gbtn');
        if (alvo) google.accounts.id.renderButton(alvo, { theme: 'filled_black', size: 'large', shape: 'pill', text: 'signin_with', locale: 'pt-BR' });
      } catch { conta.innerHTML = ''; }
    }
    async function carregar() {
      try {
        const cs = await sbGet(`comentarios?select=${CAMPOS_C}&post_id=eq.${encodeURIComponent(postId)}&order=criado_em.asc`);
        const raiz = cs.filter((c) => !c.resposta_de);
        lista.innerHTML = raiz.length ? raiz.map((c) => umComentario(c, cs.filter((r) => r.resposta_de === c.id))).join('')
          : '<li class="com-vazio">Ninguém comentou ainda. Role a iniciativa e seja a primeira pessoa!</li>';
        $c('#com-titulo').textContent = cs.length ? `${cs.length} ${cs.length === 1 ? 'comentário' : 'comentários'} na mesa` : 'Puxe uma cadeira e comente';
        if (location.hash.startsWith('#c-')) document.getElementById(location.hash.slice(1))?.scrollIntoView({ block: 'center' });
      } catch { lista.innerHTML = '<li class="com-vazio">Não consegui carregar os comentários agora.</li>'; }
    }
    lista.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-responder]'); if (!b) return;
      responderA(b.dataset.responder, b.dataset.nome);
      form.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    $c('#cancelar-resposta').addEventListener('click', () => responderA(null));
    form.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      if ($c('#com-site').value) return; // robô
      const n = nome.value.trim(), t = texto.value.trim();
      if (!sessao && n.length < 2) { msg.textContent = 'Escreva seu nome.'; nome.focus(); return; }
      if (t.length < 2) { msg.textContent = 'Escreva o comentário.'; texto.focus(); return; }
      const botao = form.querySelector('button[type=submit]');
      botao.disabled = true; msg.textContent = 'Enviando…';
      try {
        let erro = '';
        if (sessao) {
          const { error } = await (await leitor()).from('comentarios')
            .insert({ post_id: postId, resposta_de: respondendo, nome: n || 'Leitor', texto: t, user_id: sessao.user.id });
          if (error) erro = error.message || 'erro';
        } else {
          const r = await fetch(`${SB.url}/rest/v1/comentarios`, { method: 'POST',
            headers: { apikey: SB.chave, Authorization: `Bearer ${SB.chave}`, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
            body: JSON.stringify({ post_id: postId, resposta_de: respondendo, nome: n, texto: t, visitante: visitante() }) });
          if (!r.ok) erro = (await r.json().catch(() => ({}))).message || 'erro';
        }
        if (erro) {
          throw new Error(erro === 'devagar' ? 'Calma, aventureiro! Espere um pouquinho antes de comentar de novo.'
            : erro === 'muitos_links' ? 'Use no máximo 2 links por comentário.' : 'Não consegui publicar agora. Tente de novo em instantes.');
        }
        if (!sessao) guardado('pd_nome', n);
        texto.value = ''; responderA(null); msg.textContent = 'Comentário publicado. Valeu!';
        await carregar();
      } catch (err) { msg.textContent = err.message; }
      botao.disabled = false;
    });
    carregar();
    mostrarConta();
    // quem já entrou com o Google em outra visita continua logado
    if (guardado('pd-leitor')) {
      try { const sb = await leitor(); sessao = (await sb.auth.getSession()).data.session; mostrarConta(); } catch { /* segue como visitante */ }
    }
    setInterval(() => caixa.querySelectorAll('time.com-data').forEach((el) => { el.textContent = tempo(el.getAttribute('datetime')); }), 60000);
  }

  // Contagem anônima de acessos nas páginas do blog (mesma lógica do site; admins logados não contam)
  function rastro() {
    try {
      const robo = navigator.webdriver || /bot|crawl|spider|slurp|preview|lighthouse|headless|facebookexternalhit|whatsapp/i.test(navigator.userAgent);
      const admin = Object.keys(localStorage).some((k) => /^sb-.+-auth-token$/.test(k));
      if (robo || admin || /^(localhost|127\.)/.test(location.hostname)) return;
      const uuid = () => crypto.randomUUID();
      let v = localStorage.getItem('pd_v'); if (!v) { v = uuid(); localStorage.setItem('pd_v', v); }
      let s = null, nova = false;
      try { const x = JSON.parse(localStorage.getItem('pd_s') || 'null'); if (x && Date.now() - x.t < 30 * 60000) s = x.id; } catch { /* ignora */ }
      if (!s) { s = uuid(); nova = true; }
      const ua = navigator.userAgent, aparelho = /iPad|Tablet/i.test(ua) ? 'tablet' : /Mobi|Android|iPhone/i.test(ua) ? 'celular' : 'computador';
      const enviar = (ev) => {
        localStorage.setItem('pd_s', JSON.stringify({ id: s, t: Date.now() }));
        fetch(`${SB.url}/rest/v1/eventos`, { method: 'POST', keepalive: true,
          headers: { apikey: SB.chave, Authorization: `Bearer ${SB.chave}`, 'Content-Type': 'application/json', Prefer: 'return=minimal' },
          body: JSON.stringify({ visitante: v, visita: s, aparelho, ...ev }) }).catch(() => {});
      };
      let origem = null;
      if (nova) {
        const p = new URLSearchParams(location.search); let h = '';
        try { h = new URL(document.referrer).hostname.replace(/^(www|m|l|lm)\./, ''); } catch { /* sem referrer */ }
        const f = (p.get('utm_source') || (h && h !== location.hostname.replace(/^www\./, '') ? h : '')).toLowerCase();
        origem = f ? ([[/youtube|youtu\.be/, 'YouTube'], [/instagram/, 'Instagram'], [/whatsapp|wa\.me/, 'WhatsApp'], [/facebook/, 'Facebook'], [/tiktok/, 'TikTok'],
          [/discord/, 'Discord'], [/mesaquest/, 'MesaQuest'], [/google\./, 'Google'], [/bing\./, 'Bing']].find(([re]) => re.test(f))?.[1] || f).slice(0, 80) : null;
      }
      const pagina = location.pathname.slice(0, 120);
      enviar({ tipo: 'pagina', pagina, origem });
      document.addEventListener('click', (e) => {
        const el = e.target.closest('a, button'); if (!el) return;
        const area = el.closest('.topo') ? 'Menu' : el.closest('.comentarios') ? 'Blog: comentários' : el.closest('article.post') ? 'Blog: post' : el.closest('.mais') ? 'Blog: mais posts' : 'Blog: lista';
        let alvo = (el.querySelector('h3')?.textContent || el.textContent || '').replace(/\s+/g, ' ').trim();
        if (alvo.length > 80) alvo = alvo.slice(0, 77) + '…';
        let destino = el.getAttribute('href') || null;
        try { if (destino) { const u = new URL(destino, location.href); destino = u.hostname === location.hostname ? u.pathname + u.search + u.hash : u.hostname.replace(/^www\./, ''); } } catch { /* ignora */ }
        enviar({ tipo: 'clique', pagina, area, alvo: alvo || '(sem texto)', destino: destino && destino.slice(0, 120) });
      }, true);
    } catch { /* sem localStorage: não conta */ }
  }

  window.BlogPD = { SB, listar, card, artigo, limpar, esc, dataLonga, urlPost, rastro, sbGet, caixaComentarios, comentarios };
})();
