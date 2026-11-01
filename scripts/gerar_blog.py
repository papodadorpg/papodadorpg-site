#!/usr/bin/env python3
"""Gera as páginas estáticas do blog a partir dos posts publicados no Supabase.

Uso: python3 -I gerar_blog.py <pasta_do_site>
Escreve:
  blog/index.html          lista de posts (a página também atualiza sozinha pelo Supabase)
  blog/<slug>/index.html   uma página por post (Google + prévia no WhatsApp/Instagram)
  404.html                 mostra posts que acabaram de sair e ainda não têm página
  sitemap.xml, robots.txt
  img/blog/...             imagens dos posts copiadas do Supabase (e a prévia og/<slug>.jpg)
Se não conseguir ler o Supabase, não mexe em nada.
"""
import html, json, os, re, shutil, sys, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

import nh3

SITE = "https://papodadorpg.com.br"
TZ_BR = timezone(timedelta(hours=-3))
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
AUTORES = {"Henrique Müller": "/img/henrique.webp", "Elisinha Müller": "/img/elisinha.webp"}
MARCA = '<meta name="generator" content="gerar_blog.py">'
TAGS = {"p", "br", "h2", "h3", "strong", "b", "em", "i", "u", "s", "a", "ul", "ol", "li", "blockquote", "img", "iframe", "span", "hr", "pre", "code"}
ATRIBUTOS = {"a": {"href", "target"}, "img": {"src", "alt", "width", "height"}, "iframe": {"src", "allowfullscreen", "frameborder", "allow", "title"}}
e = lambda s: html.escape(str(s or ""), quote=True)


def baixar(url, binario=False, cab=None):
    req = urllib.request.Request(url, headers={"User-Agent": "papodadorpg-blog", **(cab or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = r.read()
    return d if binario else d.decode("utf8")


def data_longa(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TZ_BR)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def limpar(conteudo):
    c = nh3.clean(conteudo or "", tags=TAGS, attributes=ATRIBUTOS, link_rel="noopener", url_schemes={"http", "https", "mailto"})
    # iframes só do YouTube; imagens com carregamento preguiçoso
    c = re.sub(r'<iframe[^>]*src="(?!https://www\.youtube(?:-nocookie)?\.com/embed/)[^"]*"[^>]*>\s*</iframe>', "", c)
    c = re.sub(r"<iframe ", '<iframe loading="lazy" ', c)
    return re.sub(r"<img ", '<img loading="lazy" ', c)


class Imagens:
    """Copia para img/blog/ as imagens guardadas no Supabase (o site serve as cópias, poupando o plano gratuito)."""

    def __init__(self, pasta, base_storage):
        self.pasta, self.base = pasta, base_storage

    def local(self, url):
        if not url or not url.startswith(self.base):
            return url
        nome = re.sub(r"[^a-zA-Z0-9._-]+", "-", urllib.parse.unquote(url[len(self.base):]))
        destino = os.path.join(self.pasta, "img", "blog", nome)
        if not os.path.exists(destino):
            try:
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                open(destino, "wb").write(baixar(url, binario=True))
            except Exception as err:
                print(f"imagem não copiada ({url}): {err}", file=sys.stderr)
                return url
        return f"/img/blog/{nome}"

    def no_texto(self, conteudo):
        return re.sub(r'src="([^"]+)"', lambda m: f'src="{e(self.local(html.unescape(m.group(1))))}"', conteudo)

    def og(self, slug, capa_local):
        """Prévia para WhatsApp/Instagram: JPEG 1200x630."""
        if not capa_local or not capa_local.startswith("/img/"):
            return f"{SITE}/img/og.jpg"
        nome = f"img/blog/og/{slug}.jpg"
        destino = os.path.join(self.pasta, nome)
        try:
            from PIL import Image, ImageOps
            img = Image.open(os.path.join(self.pasta, capa_local.lstrip("/"))).convert("RGB")
            img = ImageOps.fit(img, (1200, 630))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            img.save(destino, "JPEG", quality=85)
            return f"{SITE}/{nome}"
        except Exception as err:
            print(f"prévia de {slug} não gerada: {err}", file=sys.stderr)
            return f"{SITE}/img/og.jpg"


def cabeca(titulo, descricao, url, imagem, tipo="website", extra=""):
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
{MARCA}
<title>{e(titulo)}</title>
<meta name="description" content="{e(descricao)}">
<meta name="theme-color" content="#0E1426">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="{tipo}">
<meta property="og:site_name" content="Papo Dado RPG">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descricao)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(imagem)}">
<meta property="og:locale" content="pt_BR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{e(imagem)}">
<link rel="icon" href="/img/icone.svg" type="image/svg+xml">
<link rel="alternate" type="application/rss+xml" title="Blog do Papo Dado RPG" href="/blog/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,700;12..96,800&display=swap">
<link rel="stylesheet" href="/blog/blog.css">
{extra}</head>
<body>
<div class="faixa" aria-hidden="true"></div>
<header class="topo"><div class="wrap">
  <a class="marca" href="/" aria-label="Papo Dado RPG, início"><img src="/img/logo-horizontal.svg" alt="Papo Dado RPG" width="210" height="34"></a>
  <nav class="menu" aria-label="Seções">
    <a class="so-largo" href="/#agenda">Agenda</a><a class="so-largo" href="/#mesas">Campanhas</a><a href="/#jogue">Jogar</a><a href="/blog/" aria-current="page">Blog</a>
  </nav>
</div></header>
"""


RODAPE = """<footer class="rodape"><div class="wrap">
  <img src="/img/icone.svg" alt="" width="40" height="40">
  <span>© Papo Dado RPG · O seu canal de RPG diário</span>
  <a href="/">Voltar ao site</a>
</div></footer>
<script src="/blog/blog.js"></script>
"""


def assinatura(p):
    foto = AUTORES.get(p["autor"])
    img = f'<img src="{foto}" alt="" width="32" height="32" loading="lazy">' if foto else '<span class="sem-foto" aria-hidden="true"></span>'
    return f'<span class="assinatura">{img}<span><strong>{e(p["autor"])}</strong> · {e(data_longa(p["publicar_em"]))}</span></span>'


def card(p):
    cats = "".join(f'<span class="chip">{e(c)}</span>' for c in p.get("categorias") or [])
    capa = f'<img src="{e(p["_capa"])}" alt="" loading="lazy" width="640" height="360">' if p.get("_capa") else ""
    return f"""<a class="post-card" href="/blog/{p['slug']}/" data-cats="{e('|'.join(p.get('categorias') or []))}">
      <div class="capa">{capa}</div>
      <div class="corpo">{f'<div class="cats">{cats}</div>' if cats else ''}<h3>{e(p['titulo'])}</h3>{f'<p>{e(p["resumo"])}</p>' if p.get('resumo') else ''}{assinatura(p)}</div></a>"""


def pagina_post(p, outros, nomes_campanha, img):
    url = f"{SITE}/blog/{p['slug']}/"
    descricao = p.get("resumo") or re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", p.get("conteudo") or "")).strip()[:180]
    cats = "".join(f'<a class="chip" href="/blog/?categoria={urllib.parse.quote(c)}">{e(c)}</a>' for c in p.get("categorias") or [])
    capa = f'<div class="capa-post"><img src="{e(p["_capa"])}" alt="" width="1200" height="675"></div>' if p.get("_capa") else ""
    camp = ""
    if p.get("campanha"):
        camp = (f'<div class="campanha-ligada"><span>Este post é sobre <strong>{e(nomes_campanha.get(p["campanha"], p["campanha"]))}</strong>.</span>'
                f'<a class="btn btn-linha" href="/#/campanha/{e(p["campanha"])}">Ver a campanha</a></div>')
    ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": p["titulo"], "description": descricao,
          "datePublished": p["publicar_em"], "dateModified": p.get("atualizado_em") or p["publicar_em"], "author": {"@type": "Person", "name": p["autor"]},
          "image": p["_og"], "mainEntityOfPage": url, "publisher": {"@type": "Organization", "name": "Papo Dado RPG", "logo": {"@type": "ImageObject", "url": f"{SITE}/img/icone.svg"}}}
    extra = f'<meta property="article:published_time" content="{e(p["publicar_em"])}">\n<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>\n'
    mais = "".join(card(o) for o in outros)
    return (cabeca(f"{p['titulo']} · Blog do Papo Dado RPG", descricao, url, p["_og"], "article", extra) + f"""
<main>
  <article class="post wrap estreito">
    <a class="voltar" href="/blog/">← Todos os posts</a>
    <h1>{e(p['titulo'])}</h1>
    {f'<p class="linha-fina">{e(p["resumo"])}</p>' if p.get('resumo') else ''}
    <div class="meta">{assinatura(p)}{cats}</div>
    {capa}
    <div class="texto">{img.no_texto(limpar(p.get('conteudo')))}</div>
    {camp}
  </article>
  {f'<section class="mais"><div class="wrap"><div class="rotulo">Continue lendo</div><h2>Mais do blog</h2><div class="posts">{mais}</div></div></section>' if mais else ''}
</main>
""" + RODAPE + "<script>BlogPD.rastro();</script>\n</body>\n</html>\n")


def pagina_lista(posts):
    cats = sorted({c for p in posts for c in p.get("categorias") or []}, key=str.lower)
    filtros = "".join(f'<button type="button" data-cat="{e(c)}" aria-pressed="false">{e(c)}</button>' for c in cats)
    cards = "".join(card(p) for p in posts) or '<p class="vazio">Nenhum post ainda. Volte em breve!</p>'
    return (cabeca("Blog · Papo Dado RPG", "Bastidores, dicas de mestre, resenhas e novidades das mesas do Papo Dado RPG.", f"{SITE}/blog/", f"{SITE}/img/og.jpg") + f"""
<main class="wrap">
  <div class="cab-blog"><div class="rotulo">Blog</div><h1>Do outro lado do escudo</h1>
    <p>Bastidores das mesas, dicas de mestre, resenhas e novidades do Papo Dado RPG.</p></div>
  <div class="filtros" id="filtros"{'' if cats else ' hidden'}><button type="button" data-cat="" aria-pressed="true">Todos</button>{filtros}</div>
  <div class="posts" id="posts">{cards}</div>
</main>
""" + RODAPE + """<script>
// a lista já vem pronta; aqui ela é atualizada pelo Supabase (posts que acabaram de sair) e filtrada por categoria
(function () {
  const caixa = document.getElementById('posts'), filtros = document.getElementById('filtros');
  let cat = new URLSearchParams(location.search).get('categoria') || '';
  function aplicar() {
    filtros.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.cat === cat)));
    caixa.querySelectorAll('.post-card').forEach((c) => { c.hidden = !!cat && !(c.dataset.cats || '').split('|').includes(cat); });
  }
  filtros.addEventListener('click', (ev) => {
    const b = ev.target.closest('button'); if (!b) return;
    cat = b.dataset.cat; history.replaceState(null, '', cat ? `?categoria=${encodeURIComponent(cat)}` : location.pathname); aplicar();
  });
  BlogPD.listar().then((posts) => {
    if (!posts.length) return;
    caixa.innerHTML = posts.map(BlogPD.card).join('');
    const todas = [...new Set(posts.flatMap((p) => p.categorias || []))].sort((a, b) => a.localeCompare(b, 'pt-BR'));
    filtros.hidden = !todas.length;
    filtros.innerHTML = '<button type="button" data-cat="" aria-pressed="true">Todos</button>' + todas.map((c) => `<button type="button" data-cat="${BlogPD.esc(c)}" aria-pressed="false">${BlogPD.esc(c)}</button>`).join('');
    aplicar();
  }).catch(() => {});
  aplicar();
  BlogPD.rastro();
})();
</script>
</body>
</html>
""")


def pagina_404():
    return (cabeca("Página não encontrada · Papo Dado RPG", "Página não encontrada.", f"{SITE}/", f"{SITE}/img/og.jpg",
                   extra='<meta name="robots" content="noindex">\n<script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.6/dist/purify.min.js"></script>\n') + """
<main id="conteudo">
  <div class="wrap estreito cab-blog" id="nao-achou" hidden>
    <div class="rotulo">Erro 404</div><h1>Essa página rolou 1 no dado</h1>
    <p>Não encontramos o que você procurava. <a href="/">Voltar ao site</a> ou <a href="/blog/">ver o blog</a>.</p>
  </div>
</main>
""" + RODAPE + """<script>
// post recém-publicado (a página própria fica pronta em instantes): mostra direto do Supabase
(async function () {
  const m = location.pathname.match(/^\\/blog\\/([a-z0-9-]+)\\/?$/);
  const naoAchou = () => { document.getElementById('nao-achou').hidden = false; BlogPD.rastro(); };
  if (!m) return naoAchou();
  try {
    const [p] = await BlogPD.listar({ slug: m[1], conteudo: true });
    if (!p) return naoAchou();
    let nome = '';
    if (p.campanha) { try { nome = (await BlogPD.sbGet(`campanhas?select=dados&id=eq.${encodeURIComponent(p.campanha)}`))[0]?.dados?.nome || ''; } catch { /* ignora */ } }
    document.title = `${p.titulo} · Blog do Papo Dado RPG`;
    document.getElementById('conteudo').innerHTML = BlogPD.artigo(p, nome);
    BlogPD.rastro();
  } catch { naoAchou(); }
})();
</script>
</body>
</html>
""")


def feed(posts):
    itens = "".join(f"""<item><title>{e(p['titulo'])}</title><link>{SITE}/blog/{p['slug']}/</link><guid>{SITE}/blog/{p['slug']}/</guid>
<pubDate>{datetime.fromisoformat(p['publicar_em'].replace('Z', '+00:00')).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate><description>{e(p.get('resumo') or '')}</description></item>
""" for p in posts[:30])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Blog do Papo Dado RPG</title><link>{SITE}/blog/</link><description>Bastidores, dicas de mestre e novidades do Papo Dado RPG.</description><language>pt-BR</language>
{itens}</channel></rss>
"""


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else "."
    cfg = json.load(open(os.path.join(pasta, "config.json"), encoding="utf8"))
    cab = {"apikey": cfg["supabase_anon"], "Authorization": f"Bearer {cfg['supabase_anon']}"}
    try:
        posts = json.loads(baixar(f"{cfg['supabase_url']}/rest/v1/posts?select=*&order=publicar_em.desc", cab=cab))
        nomes = {c["id"]: (c.get("dados") or {}).get("nome", c["id"]) for c in json.loads(baixar(f"{cfg['supabase_url']}/rest/v1/campanhas?select=id,dados", cab=cab))}
    except Exception as err:
        print(f"Supabase indisponível; blog não foi alterado: {err}", file=sys.stderr)
        sys.exit(0)

    img = Imagens(pasta, f"{cfg['supabase_url']}/storage/v1/object/public/blog/")
    for p in posts:
        p["_capa"] = img.local(p.get("capa_url"))
        p["_og"] = img.og(p["slug"], p["_capa"])

    raiz = os.path.join(pasta, "blog")
    os.makedirs(raiz, exist_ok=True)
    slugs = {p["slug"] for p in posts}
    # remove páginas de posts que saíram do ar (só as que este script gerou)
    for nome in os.listdir(raiz):
        alvo = os.path.join(raiz, nome, "index.html")
        if nome not in slugs and os.path.isfile(alvo) and MARCA in open(alvo, encoding="utf8").read():
            shutil.rmtree(os.path.join(raiz, nome))
            print(f"removido: blog/{nome}/")
    for i, p in enumerate(posts):
        outros = [o for o in posts if o["slug"] != p["slug"]][:3]
        os.makedirs(os.path.join(raiz, p["slug"]), exist_ok=True)
        open(os.path.join(raiz, p["slug"], "index.html"), "w", encoding="utf8").write(pagina_post(p, outros, nomes, img))
        print(f"post: blog/{p['slug']}/")
    open(os.path.join(raiz, "index.html"), "w", encoding="utf8").write(pagina_lista(posts))
    open(os.path.join(raiz, "feed.xml"), "w", encoding="utf8").write(feed(posts))
    open(os.path.join(pasta, "404.html"), "w", encoding="utf8").write(pagina_404())

    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = [(f"{SITE}/", hoje), (f"{SITE}/blog/", hoje)] + [(f"{SITE}/blog/{p['slug']}/", (p.get("atualizado_em") or p["publicar_em"])[:10]) for p in posts]
    open(os.path.join(pasta, "sitemap.xml"), "w", encoding="utf8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc><lastmod>{d}</lastmod></url>\n" for u, d in urls) + "</urlset>\n")
    open(os.path.join(pasta, "robots.txt"), "w", encoding="utf8").write(f"User-agent: *\nDisallow: /admin/\nSitemap: {SITE}/sitemap.xml\n")
    print(f"{len(posts)} post(s) publicados")


if __name__ == "__main__":
    main()
