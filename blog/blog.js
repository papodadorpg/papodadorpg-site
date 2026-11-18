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
  // nome e foto de quem assina vêm do perfil editado no /admin; a lista fixa acima fica de reserva
  const perfis = sbGet('rpc/perfis_blog').then((ps) => { for (const p of ps || []) if (p.nome && p.foto_url) AUTORES[p.nome] = p.foto_url; }).catch(() => {});
  const CAMPOS = 'id,slug,titulo,resumo,capa_url,autor,categorias,campanha,publicar_em';
  // { limite, campanha, slug, conteudo }
  async function listar(o = {}) {
    let q = `posts?select=${CAMPOS}${o.conteudo ? ',conteudo' : ''}&order=publicar_em.desc`;
    if (o.campanha) q += `&campanha=eq.${encodeURIComponent(o.campanha)}`;
    if (o.slug) q += `&slug=eq.${encodeURIComponent(o.slug)}`;
    if (o.limite) q += `&limit=${o.limite}`;
    const [r] = await Promise.all([sbGet(q), perfis]);
    return r;
  }

  function assinatura(p) {
    const foto = AUTORES[p.autor];
    return `<span class="assinatura">${foto ? `<img src="${esc(foto)}" alt="" width="32" height="32" loading="lazy">` : '<span class="sem-foto" aria-hidden="true"></span>'}
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


  // ================= REAÇÕES =================
  // Só reações positivas. Cada leitor marca quantas quiser (uma de cada) e pode desmarcar; conta pelo código aleatório do navegador.
  const REACOES = [
    ['critico', '🎲', 'Acerto crítico'],
    ['inspirou', '✨', 'Me inspirou'],
    ['util', '🧭', 'Vou usar na mesa'],
    ['aprendi', '🧠', 'Aprendi algo'],
    ['divertido', '😄', 'Divertido'],
  ];
  async function rpc(nome, args) {
    const r = await fetch(`${SB.url}/rest/v1/rpc/${nome}`, { method: 'POST',
      headers: { apikey: SB.chave, Authorization: `Bearer ${SB.chave}`, 'Content-Type': 'application/json' }, body: JSON.stringify(args) });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).message || 'erro');
    return r.json();
  }
  async function reacoes(postId, antesDe) {
    if (!postId || document.getElementById('reacoes')) return;
    const caixa = document.createElement('section');
    caixa.className = 'reacoes wrap estreito'; caixa.id = 'reacoes'; caixa.setAttribute('aria-label', 'Reações ao post');
    caixa.innerHTML = `<p class="reacoes-titulo">Como foi esse post pra você?</p><div class="reacoes-lista">${REACOES.map(([t, e, n]) =>
      `<button type="button" class="reacao" data-tipo="${t}" aria-pressed="false"><span class="reacao-emoji" aria-hidden="true">${e}</span><span>${n}</span><span class="reacao-n"></span></button>`).join('')}</div>`;
    antesDe.parentNode.insertBefore(caixa, antesDe);
    // o código do navegador só é criado quando a pessoa reage (para quem recusou a contagem de visitas)
    const eu = () => visitante() || (window.__pdv ||= `t-${Math.random().toString(36).slice(2, 12)}`);
    const mostrar = (d) => caixa.querySelectorAll('.reacao').forEach((b) => {
      const n = d.contagem?.[b.dataset.tipo] || 0;
      b.querySelector('.reacao-n').textContent = n ? String(n) : '';
      b.setAttribute('aria-pressed', String((d.minhas || []).includes(b.dataset.tipo)));
    });
    try { mostrar(await rpc('reacoes_do_post', { p_post: postId, p_visitante: guardado('pd_v') || window.__pdv || null })); } catch { /* sem contagem por enquanto */ }
    caixa.addEventListener('click', async (ev) => {
      const b = ev.target.closest('.reacao'); if (!b || b.disabled) return;
      b.disabled = true;
      // resposta imediata na tela; a contagem real chega em seguida
      const marcado = b.getAttribute('aria-pressed') === 'true', el = b.querySelector('.reacao-n');
      b.setAttribute('aria-pressed', String(!marcado));
      el.textContent = String(Math.max(0, (+el.textContent || 0) + (marcado ? -1 : 1)) || '');
      if (!marcado) { b.classList.remove('pulou'); void b.offsetWidth; b.classList.add('pulou'); }
      try { mostrar(await rpc('reagir', { p_post: postId, p_tipo: b.dataset.tipo, p_visitante: eu() })); }
      catch { b.setAttribute('aria-pressed', String(marcado)); }
      b.disabled = false;
    });
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
        <div class="com-rodape">
          <button type="button" class="com-curtir" data-curtir="${esc(c.id)}" data-nome="${esc(c.nome)}" aria-pressed="false" aria-label="Curtir o comentário de ${esc(c.nome)}">${CORACAO}<span class="com-curtir-n"></span></button>
          ${respostas ? `<button type="button" class="com-responder" data-responder="${esc(c.id)}" data-nome="${esc(c.nome)}">Responder</button>` : ''}
        </div>
        ${respostas && respostas.length ? `<ol class="respostas">${respostas.map((r) => umComentario(r, null)).join('')}</ol>` : ''}
      </div>
    </li>`;
  }
  const CORACAO = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.5-4.6-9.3-9.2C1.4 8 3.4 4.5 6.9 4.5c2.1 0 3.6 1.1 5.1 3 1.5-1.9 3-3 5.1-3 3.5 0 5.5 3.5 4.2 6.8-1.8 4.6-9.3 9.2-9.3 9.2z"/></svg>';
  const ICONE = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path fill="currentColor" d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4v-4H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm3 5v2h2V9H7zm4 0v2h2V9h-2zm4 0v2h2V9h-2z"/></svg>';
  async function comentarios() {
    const caixa = document.getElementById('comentarios');
    if (!caixa || !caixa.dataset.post) return;
    const postId = caixa.dataset.post;
    compartilhar();
    reacoes(postId, caixa);
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
    // curtidas: mesmo código de visitante das reações do post (uma curtida por navegador em cada comentário)
    const eu = () => visitante() || (window.__pdv ||= `t-${Math.random().toString(36).slice(2, 12)}`);
    function pintarCurtida(b, n, minha) {
      b.setAttribute('aria-pressed', String(minha));
      b.querySelector('.com-curtir-n').textContent = n ? String(n) : '';
      b.setAttribute('aria-label', `${n ? `${n} ${n === 1 ? 'curtida' : 'curtidas'}. ` : ''}Curtir o comentário de ${b.dataset.nome}`);
    }
    async function curtidas() {
      try {
        const d = await rpc('curtidas_do_post', { p_post: postId, p_visitante: guardado('pd_v') || window.__pdv || null });
        lista.querySelectorAll('[data-curtir]').forEach((b) => pintarCurtida(b, d.contagem?.[b.dataset.curtir] || 0, (d.minhas || []).includes(b.dataset.curtir)));
      } catch { /* sem contagem por enquanto */ }
    }
    async function curtir(b) {
      if (b.disabled) return;
      b.disabled = true;
      // resposta imediata na tela; a contagem real chega em seguida
      const marcado = b.getAttribute('aria-pressed') === 'true', n = +b.querySelector('.com-curtir-n').textContent || 0;
      pintarCurtida(b, Math.max(0, n + (marcado ? -1 : 1)), !marcado);
      if (!marcado) { b.classList.remove('pulou'); void b.offsetWidth; b.classList.add('pulou'); }
      try { const d = await rpc('curtir_comentario', { p_comentario: b.dataset.curtir, p_visitante: eu() }); pintarCurtida(b, d.n, d.curtido); }
      catch { pintarCurtida(b, n, marcado); }
      b.disabled = false;
    }

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
        const [cs] = await Promise.all([sbGet(`comentarios?select=${CAMPOS_C}&post_id=eq.${encodeURIComponent(postId)}&order=criado_em.asc`), perfis]);
        const raiz = cs.filter((c) => !c.resposta_de);
        lista.innerHTML = raiz.length ? raiz.map((c) => umComentario(c, cs.filter((r) => r.resposta_de === c.id))).join('')
          : '<li class="com-vazio">Ninguém comentou ainda. Role a iniciativa e seja a primeira pessoa!</li>';
        $c('#com-titulo').textContent = cs.length ? `${cs.length} ${cs.length === 1 ? 'comentário' : 'comentários'} na mesa` : 'Puxe uma cadeira e comente';
        if (location.hash.startsWith('#c-')) document.getElementById(location.hash.slice(1))?.scrollIntoView({ block: 'center' });
        curtidas();
      } catch { lista.innerHTML = '<li class="com-vazio">Não consegui carregar os comentários agora.</li>'; }
    }
    lista.addEventListener('click', (ev) => {
      const k = ev.target.closest('[data-curtir]'); if (k) { curtir(k); return; }
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
      if (robo || admin || !contarVisitas() || /^(localhost|127\.)/.test(location.hostname)) return;
      const uuid = () => crypto.randomUUID();
      let v = localStorage.getItem('pd_v'); if (!v) { v = uuid(); localStorage.setItem('pd_v', v); }
      let s = null, nova = false;
      try { const x = JSON.parse(localStorage.getItem('pd_s') || 'null'); if (x && Date.now() - x.t < 30 * 60000) s = x.id; } catch { /* ignora */ }
      if (!s) { s = uuid(); nova = true; }
      const ua = navigator.userAgent, aparelho = /iPad|Tablet/i.test(ua) ? 'tablet' : /Mobi|Android|iPhone/i.test(ua) ? 'celular' : 'computador';
      const enviar = (ev) => {
        if (!contarVisitas()) return; // recusou no aviso de privacidade durante a visita
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
        const el = e.target.closest('a, button'); if (!el || el.closest('#aviso-priv')) return;
        const area = el.closest('.topo') ? 'Menu' : el.closest('.comentarios') ? 'Blog: comentários' : el.closest('article.post') ? 'Blog: post' : el.closest('.mais') ? 'Blog: mais posts' : 'Blog: lista';
        let alvo = (el.querySelector('h3')?.textContent || el.textContent || '').replace(/\s+/g, ' ').trim();
        if (alvo.length > 80) alvo = alvo.slice(0, 77) + '…';
        let destino = el.getAttribute('href') || null;
        try { if (destino) { const u = new URL(destino, location.href); destino = u.hostname === location.hostname ? u.pathname + u.search + u.hash : u.hostname.replace(/^www\./, ''); } } catch { /* ignora */ }
        enviar({ tipo: 'clique', pagina, area, alvo: alvo || '(sem texto)', destino: destino && destino.slice(0, 120) });
      }, true);
    } catch { /* sem localStorage: não conta */ }
  }

  // ================= MENU NO CELULAR =================
  // Botão de 3 linhas que abre, em cascata, as mesmas seções do menu do computador (só aparece em telas estreitas, pelo CSS)
  function menuCelular() {
    const topo = document.querySelector('header.topo'), nav = topo && topo.querySelector('nav.menu');
    if (!nav || topo.querySelector('.botao-menu')) return;
    if (!nav.id) nav.id = 'menu-site';
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'botao-menu';
    b.setAttribute('aria-controls', nav.id); b.setAttribute('aria-expanded', 'false'); b.setAttribute('aria-label', 'Abrir o menu');
    b.innerHTML = '<span></span><span></span><span></span>';
    nav.before(b);
    const abrir = (sim) => {
      topo.classList.toggle('menu-aberto', sim);
      b.setAttribute('aria-expanded', String(sim)); b.setAttribute('aria-label', sim ? 'Fechar o menu' : 'Abrir o menu');
    };
    b.addEventListener('click', () => abrir(!topo.classList.contains('menu-aberto')));
    nav.addEventListener('click', (e) => { if (e.target.closest('a')) abrir(false); });
    document.addEventListener('click', (e) => { if (!topo.contains(e.target)) abrir(false); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && topo.classList.contains('menu-aberto')) { abrir(false); b.focus(); } });
    matchMedia('(min-width: 861px)').addEventListener('change', (m) => { if (m.matches) abrir(false); });
  }
  // ================= COMPARTILHAR =================
  // Botões no fim de cada post: WhatsApp, Instagram, Facebook e copiar o link.
  // O Instagram não aceita links pela web: no celular abre o menu de compartilhar do aparelho (que lista o Instagram);
  // no computador copia o link para colar no Story ou no Direct.
  const ICONES_COMP = {"whatsapp": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path fill=\"currentColor\" d=\"M12 2.2A9.7 9.7 0 0 0 3.7 17l-1.4 4.8 4.9-1.3A9.7 9.7 0 1 0 12 2.2zm0 17.7c-1.5 0-2.9-.4-4.1-1.1l-.3-.2-2.9.8.8-2.8-.2-.3A8 8 0 1 1 12 19.9zm4.4-6c-.2-.1-1.4-.7-1.7-.8-.2-.1-.4-.1-.5.1l-.8 1c-.1.2-.3.2-.5.1a6.6 6.6 0 0 1-3.3-2.9c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.5-.4h-.5c-.2 0-.4.1-.6.3-.2.2-.8.8-.8 2s.9 2.3 1 2.5c.1.2 1.7 2.6 4.2 3.7 1.6.7 2.2.7 3 .6.5-.1 1.4-.6 1.6-1.1.2-.6.2-1 .1-1.1l-.6-.4z\"/></svg>", "instagram": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><rect x=\"3\" y=\"3\" width=\"18\" height=\"18\" rx=\"5\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"/><circle cx=\"12\" cy=\"12\" r=\"4.2\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"/><circle cx=\"17.4\" cy=\"6.6\" r=\"1.3\" fill=\"currentColor\"/></svg>", "facebook": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path fill=\"currentColor\" d=\"M13.5 21.5v-8h2.7l.4-3.2h-3.1V8.3c0-.9.3-1.6 1.6-1.6h1.7V3.9c-.3 0-1.3-.1-2.5-.1-2.5 0-4.2 1.5-4.2 4.3v2.3H7.4v3.2h2.7v8z\"/></svg>", "link": "<svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" d=\"M10 14a4.5 4.5 0 0 0 6.4 0l3.2-3.2a4.5 4.5 0 0 0-6.4-6.4l-1.1 1.1M14 10a4.5 4.5 0 0 0-6.4 0l-3.2 3.2a4.5 4.5 0 0 0 6.4 6.4l1.1-1.1\"/></svg>"};
  async function copiarTexto(t) {
    try { await navigator.clipboard.writeText(t); return true; } catch { /* tenta do jeito antigo */ }
    try {
      const a = document.createElement('textarea'); a.value = t; a.setAttribute('readonly', ''); a.style.position = 'fixed'; a.style.opacity = '0';
      document.body.appendChild(a); a.select(); const ok = document.execCommand('copy'); a.remove(); return ok;
    } catch { return false; }
  }
  function compartilhar() {
    const art = document.querySelector('article.post'), texto = art && art.querySelector('.texto');
    if (!texto || art.querySelector('.compartilhar')) return;
    const titulo = (art.querySelector('h1')?.textContent || document.title).trim();
    const url = location.origin + location.pathname;
    const com = (fonte) => `${url}?utm_source=${fonte}`;
    const caixa = document.createElement('div');
    caixa.className = 'compartilhar';
    caixa.innerHTML = `<p class="comp-titulo">Gostou? Mande para a sua mesa</p>
      <div class="comp-botoes">
        <a class="comp comp-whatsapp" href="https://wa.me/?text=${encodeURIComponent(`${titulo} ${com('whatsapp')}`)}" target="_blank" rel="noopener">${ICONES_COMP.whatsapp}<span>WhatsApp</span></a>
        <button type="button" class="comp comp-instagram" data-comp="instagram">${ICONES_COMP.instagram}<span>Instagram</span></button>
        <a class="comp comp-facebook" href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(com('facebook'))}" target="_blank" rel="noopener">${ICONES_COMP.facebook}<span>Facebook</span></a>
        <button type="button" class="comp comp-link" data-comp="link">${ICONES_COMP.link}<span>Copiar link</span></button>
      </div>
      <p class="comp-msg" role="status"></p>`;
    texto.after(caixa);
    const msg = caixa.querySelector('.comp-msg');
    let tempoMsg = 0;
    const avisar = (t) => { msg.textContent = t; clearTimeout(tempoMsg); tempoMsg = setTimeout(() => { msg.textContent = ''; }, 5000); };
    caixa.addEventListener('click', async (ev) => {
      const b = ev.target.closest('[data-comp]'); if (!b) return;
      if (b.dataset.comp === 'instagram' && navigator.share && matchMedia('(pointer: coarse)').matches) {
        try { await navigator.share({ title: titulo, url: com('instagram') }); } catch { /* fechou o menu */ }
        return;
      }
      const ok = await copiarTexto(b.dataset.comp === 'instagram' ? com('instagram') : url);
      avisar(!ok ? `Não consegui copiar. O link é ${url}` : b.dataset.comp === 'instagram'
        ? 'Link copiado! Agora é só colar no seu Story ou no Direct do Instagram.' : 'Link copiado!');
    });
  }

  // ================= PRIVACIDADE =================
  // Aviso na primeira visita (em todas as páginas que carregam este arquivo). A contagem anônima de visitas
  // segue até a pessoa recusar; quem recusa não é mais contado e tem os códigos de visita apagados.
  // Suba VERSAO_PRIV quando a política mudar de um jeito que peça uma nova escolha (o aviso volta para todo mundo).
  const VERSAO_PRIV = '1';
  const escolhaPriv = () => { const [e, v] = guardado('pd_privacidade').split('-'); return v === VERSAO_PRIV ? e : ''; };
  const contarVisitas = () => escolhaPriv() !== 'nao';
  const ESTILO_PRIV = `
.aviso-priv { position: fixed; z-index: 60; left: 16px; bottom: 16px; max-width: 420px; padding: 16px 18px; border-radius: 14px;
  background: #171f38; color: #fff; border: 2px solid #000; outline: 1px solid #26304f; box-shadow: 0 18px 40px rgba(0,0,0,.5);
  font: 15px/1.5 "Bricolage Grotesque", "Segoe UI", system-ui, sans-serif; }
.aviso-priv strong { display: block; font-size: 16px; margin-bottom: 4px; }
.aviso-priv p { margin: 0 0 12px; color: #d3d8ea; }
.aviso-priv a { color: #00BAFC; }
.aviso-priv .priv-botoes { display: flex; gap: 10px; flex-wrap: wrap; }
.aviso-priv button { font: inherit; font-weight: 700; font-size: 15px; padding: 9px 18px; border-radius: 999px; cursor: pointer; border: 2px solid #000; }
.aviso-priv .priv-sim { background: #FD7601; color: #000; box-shadow: 0 3px 0 #000; }
.aviso-priv .priv-nao { background: transparent; color: #fff; border-color: #26304f; }
.aviso-priv button:focus-visible { outline: 3px solid #FD7601; outline-offset: 3px; }
@media (max-width: 600px) { .aviso-priv { left: 10px; right: 10px; bottom: 10px; max-width: none; padding: 14px 16px; font-size: 14px; } .aviso-priv button { flex: 1; } }
footer.rodape .link-priv { margin-left: auto; }`;
  function avisoPrivacidade(forcar) {
    if (!document.getElementById('estilo-priv')) {
      const st = document.createElement('style'); st.id = 'estilo-priv'; st.textContent = ESTILO_PRIV; document.head.appendChild(st);
    }
    // link para a política no rodapé de todas as páginas
    const rod = document.querySelector('footer.rodape .wrap');
    if (rod && !rod.querySelector('a[href="/privacidade"]')) {
      const a = document.createElement('a'); a.href = '/privacidade'; a.className = 'link-priv'; a.textContent = 'Privacidade';
      const ult = rod.querySelector('a:last-of-type'); if (ult) ult.before(a); else rod.appendChild(a);
    }
    if ((escolhaPriv() && !forcar) || document.getElementById('aviso-priv')) return;
    const caixa = document.createElement('section');
    caixa.className = 'aviso-priv'; caixa.id = 'aviso-priv'; caixa.setAttribute('aria-label', 'Aviso de privacidade');
    caixa.innerHTML = `<strong>Cookies e privacidade</strong>
      <p>Sem anúncios e sem rastreadores de outras empresas. Guardamos no navegador só um código anônimo para contar visitas e lembrar seus comentários e reações. <a href="/privacidade">Saiba mais</a></p>
      <div class="priv-botoes"><button type="button" class="priv-sim">Aceitar</button><button type="button" class="priv-nao">Recusar</button></div>`;
    document.body.appendChild(caixa);
    caixa.addEventListener('click', (ev) => {
      const sim = ev.target.closest('.priv-sim'), nao = ev.target.closest('.priv-nao');
      if (!sim && !nao) return;
      guardado('pd_privacidade', `${sim ? 'sim' : 'nao'}-${VERSAO_PRIV}`);
      if (nao) { try { localStorage.removeItem('pd_v'); localStorage.removeItem('pd_s'); } catch { /* sem localStorage */ } }
      caixa.remove();
    });
  }
  function iniciar() {
    menuCelular();
    avisoPrivacidade();
    document.getElementById('mudar-privacidade')?.addEventListener('click', () => avisoPrivacidade(true));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar); else iniciar();

  window.BlogPD = { SB, listar, card, artigo, limpar, esc, dataLonga, urlPost, rastro, sbGet, caixaComentarios, comentarios, contarVisitas, avisoPrivacidade };
})();
