#!/usr/bin/env python3
"""Gera as páginas estáticas das campanhas e a agenda para assinar.

Uso: python3 -I gerar_campanhas.py <pasta_do_site>   (rodar depois do gerar_blog.py)
Escreve:
  campanhas/index.html          todas as campanhas (no ar e encerradas)
  campanhas/<nome>/index.html   uma página por campanha: sinopse, horário, episódios com resumo em texto,
                                último Highlight e posts do blog (o Google lê; o endereço com # do site não)
  campanhas/paginas.json        {id da campanha: endereço}; o site usa para ligar os cards a estas páginas
  agenda.ics                    todas as lives, para assinar no Google Agenda, Apple ou Outlook
  sitemap.xml                   acrescenta as páginas das campanhas ao sitemap que o gerar_blog.py escreveu
Se não conseguir ler o Supabase, não mexe em nada.
"""
import json, os, re, shutil, sys, unicodedata, urllib.parse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gerar_blog as gb  # mesmo cabeçalho, rodapé e cópia de imagens do blog

SITE = gb.SITE
TZ_BR = gb.TZ_BR
DURACAO_H = 3
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
DIAS_PLURAL = ["segundas", "terças", "quartas", "quintas", "sextas", "sábados", "domingos"]
STATUS = {"finalizada": "Campanha finalizada", "encerrada": "Campanha encerrada", "cancelada": "Campanha cancelada"}
MARCA = '<meta name="generator" content="gerar_campanhas.py">'
e = gb.e


def slug(txt):
    t = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:70] or "campanha"


def norm(txt):
    return unicodedata.normalize("NFKD", txt or "").encode("ascii", "ignore").decode().lower()


def titulo_ep(t):
    """'D&D 5.5 Maldição de Strahd - Episódio 33 | A Colina Yester' -> 'Episódio 33 · A Colina Yester'"""
    m = re.search(r"(Epis[oó]dio\s*(?:\d+|Final)|\bEp\.?\s*\d+|Sess[aã]o Zero).*", t, re.I)
    s = m.group(0) if m else (" - ".join(t.split(" - ")[1:]) if " - " in t else t)
    s = re.sub(r"^Ep\.?\s*(\d+)", lambda x: f"Episódio {x.group(1).zfill(2)}", s, flags=re.I)
    return re.sub(r"\s*\|\s*", " · ", s, count=1).strip()


def hora_txt(h, m):
    return f"{h}h{m:02d}" if m else f"{h}h"


def quando(ref, cada):
    """'2026-11-09T20:30', 14 -> 'Segundas, às 20h30 · quinzenal'"""
    d = datetime.strptime(ref[:16], "%Y-%m-%dT%H:%M")
    ritmo = {7: "toda semana", 14: "quinzenal"}.get(cada, f"a cada {cada} dias")
    return f"{DIAS_PLURAL[d.weekday()].capitalize()}, às {hora_txt(d.hour, d.minute)} · {ritmo}"


def dur_txt(d):
    p = [int(x) for x in str(d or "").split(":") if x.isdigit()]
    if len(p) == 3:
        return f"{p[0]}h{p[1]:02d}" if p[0] else f"{p[1]} min"
    return f"{p[0]} min" if len(p) == 2 else ""


# ================= PÁGINAS =================
CSS_PAGINA = ""  # o estilo fica no blog.css (classes .cp-*)


def cabeca(*args, **kw):
    """Cabeçalho do blog, com "Campanhas" marcado no menu em vez de "Blog"."""
    return (gb.cabeca(*args, **kw).replace('<a href="/blog/" aria-current="page">Blog</a>', '<a href="/blog/">Blog</a>')
            .replace('<a class="so-largo" href="/#mesas">Campanhas</a>', '<a class="so-largo" href="/campanhas/" aria-current="page">Campanhas</a>'))


def miniaturas(pasta, posts):
    """Capas dos posts em 720 px (img/blog/mini/), para cards e destaques da página inicial: a original tem 1600 px."""
    try:
        from PIL import Image
    except ImportError:
        return
    for p in posts:
        capa = p.get("_capa") or ""
        if not capa.startswith("/img/blog/"):
            continue
        nome = os.path.splitext(os.path.basename(capa))[0]
        rel = f"/img/blog/mini/{nome}.webp"
        destino = os.path.join(pasta, rel.lstrip("/"))
        if not os.path.exists(destino):
            try:
                im = Image.open(os.path.join(pasta, capa.lstrip("/"))).convert("RGB")
                im.thumbnail((720, 720))
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                im.save(destino, "WEBP", quality=80)
                print(f"miniatura: {rel}")
            except Exception as err:
                print(f"miniatura de {capa} não gerada: {err}", file=sys.stderr)
                continue
        p["_capa"] = rel


def pagina_campanha(c, eps, hls, resumos, posts, img, url):
    d = c["dados"]
    ativa = c["ativa"]
    nome = d["nome"]
    capa = img.local(d.get("capa_url")) or (f"/img/pl/{c['id']}.webp" if (d.get("playlist") or d.get("capa")) else "")
    og = f"{SITE}{capa}" if capa.startswith("/") else (capa or f"{SITE}/img/og.jpg")
    sinopse = d.get("sinopse") or ""
    descricao = (sinopse[:155] + "…") if len(sinopse) > 156 else sinopse
    rotulo = ("Nova campanha" if not eps else "No ar no canal") if ativa else STATUS.get(d.get("status"), "Campanha finalizada")
    chips = []
    if ativa and d.get("ref") and d.get("cada"):
        chips.append(f'<span class="chip cp-quando">{e(quando(d["ref"], d["cada"]))}</span>')
    if d.get("sistema"):
        chips.append(f'<span class="chip">{e(d["sistema"])}</span>')
    n = len(eps) or d.get("videos") or 0
    if n:
        chips.append(f'<span class="chip">{n} vídeos</span>')
    if d.get("mestre"):
        chips.append(f'<span class="chip">Mestre {e(d["mestre"])}</span>')
    pl = d.get("playlist")
    acoes = []
    if pl:
        inicio = f"https://www.youtube.com/watch?v={eps[0]['id']}&list={urllib.parse.quote(pl)}" if eps else f"https://www.youtube.com/playlist?list={urllib.parse.quote(pl)}"
        acoes.append(f'<a class="btn btn-play" href="{e(inicio)}" target="_blank" rel="noopener">Assistir do começo</a>')
        acoes.append(f'<a class="btn btn-linha" href="https://www.youtube.com/playlist?list={e(urllib.parse.quote(pl))}" target="_blank" rel="noopener">Playlist no YouTube</a>')
    else:
        acoes.append('<a class="btn btn-play" href="https://www.youtube.com/@papodadorpg?sub_confirmation=1" target="_blank" rel="noopener">Inscrever-se no canal</a>')
    if ativa:
        acoes.append('<a class="btn btn-linha" href="/#agenda">Ver a agenda</a>')
    sobre = "".join(f'<p class="cp-sinopse">{e(t)}</p>' for t in (d.get("sobre") or []))

    ultima = ""
    if hls:
        h = hls[0]
        ultima = f"""<section class="cp-bloco"><div class="cp-ultima">
      <a class="cp-mini" href="https://www.youtube.com/watch?v={e(h['id'])}" target="_blank" rel="noopener" tabindex="-1">{f'<img src="/{e(h["capa"])}" alt="" loading="lazy" width="480" height="270">' if h.get('capa') else ''}<span class="cp-play" aria-hidden="true"></span></a>
      <div><div class="rotulo">Na última sessão</div><h2>{e(titulo_ep(h['titulo']))}</h2>
        <p>Perdeu a live? Os melhores momentos do episódio{f" em {dur_txt(h.get('duracao'))}" if dur_txt(h.get('duracao')) else ''}, sem pausa nem discussão de regra.</p>
        <a class="btn btn-play" href="https://www.youtube.com/watch?v={e(h['id'])}" target="_blank" rel="noopener">Assistir ao resumo</a></div>
    </div></section>"""

    lista = ""
    if eps:
        itens = []
        for i, ep in enumerate(eps):
            link = f"https://www.youtube.com/watch?v={ep['id']}" + (f"&list={urllib.parse.quote(pl)}" if pl else "")
            texto = resumos.get(ep["id"], "")
            corpo = "".join(f"<p>{e(par)}</p>" for par in re.split(r"\n{2,}", texto.strip()) if par.strip()) if texto else ""
            itens.append(f"""<li id="ep-{e(ep['id'])}"{' class="com-resumo"' if corpo else ''}>
        <a href="{e(link)}" target="_blank" rel="noopener"><span class="n">{i + 1}</span><span class="t">{e(titulo_ep(ep['titulo']))}</span><span class="d">{e(ep.get('duracao') or '')}</span></a>
        {f'<div class="cp-resumo">{corpo}</div>' if corpo else ''}</li>""")
        com = sum(1 for ep in eps if ep["id"] in resumos)
        lista = f"""<section class="cp-bloco"><div class="rotulo">Episódios</div>
      <h2>{len(eps)} {'vídeo' if len(eps) == 1 else 'vídeos'}, do primeiro ao mais recente</h2>
      {f'<p class="cp-dica">{com} {"episódio tem" if com == 1 else "episódios têm"} resumo em texto, para quem quer pegar o fio da história sem assistir tudo.</p>' if com else ''}
      <ol class="cp-episodios">{''.join(itens)}</ol></section>"""
    elif ativa:
        lista = """<section class="cp-bloco"><div class="rotulo">Estreia</div><h2>Os episódios aparecem aqui assim que a campanha estrear</h2>
      <p>Ative o sino no YouTube ou assine a agenda do canal para não perder a estreia.</p></section>"""

    blog = ""
    if posts:
        blog = f"""<section class="cp-bloco"><div class="rotulo">No blog</div><h2>Posts sobre esta campanha</h2>
      <div class="posts">{''.join(gb.card(p) for p in posts)}</div></section>"""

    ld = {"@context": "https://schema.org", "@type": "CreativeWorkSeries", "name": nome, "description": sinopse, "url": url,
          "image": og, "inLanguage": "pt-BR", "genre": "RPG de mesa ao vivo", "creator": {"@type": "Organization", "name": "Papo Dado RPG", "url": SITE}}
    if eps:
        ld["hasPart"] = [{"@type": "VideoObject", "name": ep["titulo"], "url": f"https://www.youtube.com/watch?v={ep['id']}",
                          "thumbnailUrl": f"https://i.ytimg.com/vi/{ep['id']}/hqdefault.jpg", **({"description": resumos[ep["id"]][:300]} if ep["id"] in resumos else {})}
                         for ep in eps[-20:]]
    ld_txt = json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")
    extra = f'{MARCA}\n<script type="application/ld+json">{ld_txt}</script>\n'
    titulo = f"{nome} · RPG ao vivo no Papo Dado RPG"
    proxima = f'<p class="cp-proxima" id="cp-proxima" data-campanha="{e(c["id"])}" data-ref="{e(d.get("ref", ""))}" data-cada="{e(d.get("cada", ""))}" hidden></p>' if ativa else ""
    return (cabeca(titulo, descricao or f"{nome}: campanha de RPG de mesa ao vivo no canal Papo Dado RPG.", url, og, "website", extra) + f"""
<main class="cp" style="--cor:{e(COR.get(d.get('cor'), '#FD7601'))}">
  <div class="wrap">
    <a class="voltar" href="/campanhas/">← Todas as campanhas</a>
    <div class="cp-topo">
      <div class="cp-capa">{f'<img src="{e(capa)}" alt="Capa de {e(nome)}" width="854" height="480">' if capa else ''}</div>
      <div>
        <div class="rotulo">{e(rotulo)}</div>
        <h1>{e(nome)}</h1>
        <div class="cp-chips">{''.join(chips)}</div>
        <p class="cp-sinopse">{e(sinopse)}</p>
        {sobre}
        {proxima}
        <div class="cp-acoes">{''.join(acoes)}</div>
      </div>
    </div>
    {ultima}
    {lista}
    {blog}
    <section class="cp-bloco cp-chamada"><div><div class="rotulo">Quer jogar também?</div><h2>Puxe uma cadeira</h2>
      <p>Algumas mesas recebem jogadores pelo MesaQuest quando abre vaga, e a comunidade do WhatsApp avisa primeiro.</p></div>
      <div class="cp-acoes"><a class="btn btn-play" href="/#jogue">Jogue com a gente</a><a class="btn btn-linha" href="/#comunidade">Comunidade</a></div></section>
  </div>
</main>
""" + gb.RODAPE + PROXIMA_JS + "</body>\n</html>\n")


# vermelho um pouco mais escuro que o da marca para o texto branco do chip ter contraste suficiente
COR = {"ciano": "#00BAFC", "azul": "#005DFB", "roxo": "#7020F9", "vermelho": "#E00B33", "laranja": "#FD7601"}

# próxima live calculada no navegador (com cancelamentos e remarcações do /admin), igual à página inicial
PROXIMA_JS = """<script>
(async function () {
  BlogPD.rastro();
  const el = document.getElementById('cp-proxima'); if (!el || !el.dataset.ref) return;
  const cada = +el.dataset.cada * 86400000, J = 3 * 3600000, agora = Date.now();
  const br = (iso) => new Date(iso + ':00-03:00').getTime();
  const dia = (t) => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(t));
  let exc = [];
  try { exc = await BlogPD.sbGet(`excecoes?select=data,acao,novo_inicio&campanha=eq.${encodeURIComponent(el.dataset.campanha)}&data=gte.${dia(agora - 86400000)}`); } catch { /* segue sem */ }
  const ref = br(el.dataset.ref.slice(0, 16));
  let t = agora < ref ? ref : ref + Math.ceil((agora - J - ref) / cada) * cada;
  for (let i = 0; i < 12; i++, t += cada) {
    const x = exc.find((e) => e.data === dia(t));
    if (x?.acao === 'cancelada') continue;
    const ini = x?.acao === 'remarcada' && x.novo_inicio ? br(x.novo_inicio.slice(0, 16)) : t;
    if (ini + J < agora) continue;
    const txt = new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }).format(new Date(ini));
    const bonito = txt.replace(/(\\d{1,2}):(\\d{2})/, (_, h, m) => (m === '00' ? `${+h}h` : `${+h}h${m}`));
    el.innerHTML = ini <= agora ? '<strong>Ao vivo agora</strong> no YouTube' : `Próxima live: <strong>${bonito}</strong>${x?.acao === 'remarcada' ? ' (remarcada)' : ''}`;
    el.hidden = false; return;
  }
})();
</script>
"""


def pagina_lista(camps, paginas, img):
    def card(c):
        d = c["dados"]
        capa = img.local(d.get("capa_url")) or (f"/img/pl/{c['id']}.webp" if (d.get("playlist") or d.get("capa")) else "")
        sub = quando(d["ref"], d["cada"]) if c["ativa"] and d.get("ref") and d.get("cada") else STATUS.get(d.get("status"), "Finalizada")
        return f"""<a class="post-card" href="/campanhas/{paginas[c['id']]}/">
      <div class="capa">{f'<img src="{e(capa)}" alt="" loading="lazy" width="640" height="360">' if capa else ''}</div>
      <div class="corpo"><div class="cats"><span class="chip">{e(sub)}</span>{f'<span class="chip">{e(d["sistema"])}</span>' if d.get('sistema') else ''}</div>
        <h3>{e(d['nome'])}</h3><p>{e(d.get('sinopse') or '')}</p></div></a>"""
    ativas = [c for c in camps if c["ativa"] and not c["dados"].get("programa")]
    fim = [c for c in camps if not c["ativa"]]
    return (cabeca("Campanhas de RPG ao vivo · Papo Dado RPG", "Todas as campanhas de RPG de mesa do canal Papo Dado RPG: as que estão no ar, com dia e horário, e as já finalizadas para maratonar.",
                      f"{SITE}/campanhas/", f"{SITE}/img/og.jpg", extra=MARCA + "\n") + f"""
<main class="wrap">
  <div class="cab-blog"><div class="rotulo">Campanhas</div><h1>Toda semana na mesa</h1>
    <p>As campanhas de RPG que vão ao ar ao vivo no YouTube e as que já terminaram, para maratonar do começo.</p></div>
  <h2 class="cp-secao">No ar no canal</h2>
  <div class="posts">{''.join(card(c) for c in ativas)}</div>
  {f'<h2 class="cp-secao">Para maratonar: campanhas finalizadas</h2><div class="posts">{"".join(card(c) for c in fim)}</div>' if fim else ''}
</main>
""" + gb.RODAPE + "<script>BlogPD.rastro();</script>\n</body>\n</html>\n")


# ================= AGENDA (.ics) =================
def ics_txt(s):
    return str(s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_linha(txt):
    """Quebra linhas longas (máx. 75 bytes), como pede o formato."""
    b = txt.encode("utf8")
    if len(b) <= 75:
        return txt + "\r\n"
    partes, atual = [], ""
    for ch in txt:
        if len((atual + ch).encode("utf8")) > (75 if not partes else 74):
            partes.append(atual); atual = ""
        atual += ch
    partes.append(atual)
    return "\r\n ".join(partes) + "\r\n"


def agenda_ics(camps, paginas, excs):
    agora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Papo Dado RPG//Agenda das lives//PT-BR", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:Papo Dado RPG · lives", "X-WR-CALDESC:Todas as lives de RPG do canal Papo Dado RPG. Atualiza sozinha quando muda horário ou data.",
         "X-WR-TIMEZONE:America/Sao_Paulo", "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H",
         "BEGIN:VTIMEZONE", "TZID:America/Sao_Paulo", "BEGIN:STANDARD", "DTSTART:19700101T000000", "TZOFFSETFROM:-0300", "TZOFFSETTO:-0300", "TZNAME:-03", "END:STANDARD", "END:VTIMEZONE"]
    for c in camps:
        d = c["dados"]
        if not (c["ativa"] and d.get("ref") and d.get("cada")):
            continue
        ini = datetime.strptime(d["ref"][:16], "%Y-%m-%dT%H:%M")
        hora = ini.strftime("%H%M%S")
        pagina = f"{SITE}/campanhas/{paginas[c['id']]}/" if c["id"] in paginas else f"{SITE}/#agenda"
        desc = f"{d.get('sinopse') or ''}\n\nAo vivo no YouTube: https://www.youtube.com/@papodadorpg/streams\nSobre a campanha: {pagina}"
        titulo = f"{d['nome']} · live no Papo Dado RPG"
        uid = f"{c['id']}@papodadorpg.com.br"
        semanas = max(1, round(int(d["cada"]) / 7))
        minhas = [x for x in excs if x["campanha"] == c["id"]]
        exdates = [x for x in minhas if x["acao"] in ("cancelada", "remarcada")]
        L += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{agora}", f"DTSTART;TZID=America/Sao_Paulo:{ini.strftime('%Y%m%dT%H%M%S')}",
              f"DURATION:PT{DURACAO_H}H", f"RRULE:FREQ=WEEKLY;INTERVAL={semanas}", f"SUMMARY:{ics_txt(titulo)}", f"DESCRIPTION:{ics_txt(desc)}",
              "LOCATION:https://www.youtube.com/@papodadorpg", f"URL:{pagina}"]
        L += [f"EXDATE;TZID=America/Sao_Paulo:{x['data'].replace('-', '')}T{hora}" for x in exdates]
        L.append("END:VEVENT")
        for x in minhas:
            if x["acao"] == "remarcada" and x.get("novo_inicio"):
                novo = datetime.strptime(x["novo_inicio"][:16], "%Y-%m-%dT%H:%M")
                L += ["BEGIN:VEVENT", f"UID:{c['id']}-{x['data']}@papodadorpg.com.br", f"DTSTAMP:{agora}",
                      f"DTSTART;TZID=America/Sao_Paulo:{novo.strftime('%Y%m%dT%H%M%S')}", f"DURATION:PT{DURACAO_H}H",
                      f"SUMMARY:{ics_txt(titulo + ' (remarcada)')}", f"DESCRIPTION:{ics_txt((x.get('nota') or 'Sessão remarcada.') + chr(10) + chr(10) + desc)}",
                      "LOCATION:https://www.youtube.com/@papodadorpg", f"URL:{pagina}", "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "".join(ics_linha(x) for x in L)


# ================= PRINCIPAL =================
def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else "."
    cfg = json.load(open(os.path.join(pasta, "config.json"), encoding="utf8"))
    cab = {"apikey": cfg["supabase_anon"], "Authorization": f"Bearer {cfg['supabase_anon']}"}
    base = cfg["supabase_url"] + "/rest/v1/"
    try:
        camps = json.loads(gb.baixar(base + "campanhas?select=id,ativa,ordem,dados&order=ordem,id", cab=cab))
        desde = (datetime.now(TZ_BR) - timedelta(days=60)).strftime("%Y-%m-%d")
        excs = json.loads(gb.baixar(base + f"excecoes?select=campanha,data,acao,novo_inicio,nota&data=gte.{desde}", cab=cab))
        resumos_l = json.loads(gb.baixar(base + "episodios_resumos?select=video_id,texto", cab=cab))
        posts = json.loads(gb.baixar(base + "posts?select=*&order=publicar_em.desc", cab=cab))
    except Exception as err:
        print(f"Supabase indisponível; campanhas não foram alteradas: {err}", file=sys.stderr)
        sys.exit(0)
    camps = [c for c in camps if (c.get("dados") or {}).get("nome")]
    resumos = {r["video_id"]: r["texto"] for r in resumos_l}
    try:
        epis = json.load(open(os.path.join(pasta, "episodios.json"), encoding="utf8"))
    except Exception:
        epis = {"campanhas": {}, "highlights": []}
    img = gb.Imagens(pasta, f"{cfg['supabase_url']}/storage/v1/object/public/blog/")
    try:  # nome e foto de quem assina os posts (perfil do /admin)
        for pf in json.loads(gb.baixar(base + "rpc/perfis_blog", cab=cab)):
            if pf.get("nome") and pf.get("foto_url"):
                gb.AUTORES[pf["nome"]] = img.local(pf["foto_url"])
    except Exception:
        pass
    for p in posts:
        p["_capa"] = img.local(p.get("capa_url"))
    miniaturas(pasta, posts)

    # endereço de cada campanha: nome sem acento; o "programa" (Live de Almoço) não ganha página
    paginas, usados = {}, set()
    for c in camps:
        if c["dados"].get("programa"):
            continue
        s = slug(c["dados"]["nome"])
        if s in usados:
            s = f"{s}-{c['id']}"
        usados.add(s); paginas[c["id"]] = s

    raiz = os.path.join(pasta, "campanhas")
    os.makedirs(raiz, exist_ok=True)
    for nome in os.listdir(raiz):  # páginas de campanhas que saíram (só as que este script gerou)
        alvo = os.path.join(raiz, nome, "index.html")
        if nome not in paginas.values() and os.path.isfile(alvo) and MARCA in open(alvo, encoding="utf8").read():
            shutil.rmtree(os.path.join(raiz, nome)); print(f"removido: campanhas/{nome}/")
    hl_todos = epis.get("highlights") or []
    numero = lambda t: int((re.search(r"(?:Epis[oó]dio|Ep\.?)\s*(\d+)", t, re.I) or [0, 0])[1])
    for c in camps:
        if c["id"] not in paginas:
            continue
        d = c["dados"]
        eps = (epis.get("campanhas", {}).get(c["id"]) or {}).get("episodios") or []
        hls = sorted([h for h in hl_todos if norm(d["nome"]) in norm(h["titulo"])], key=lambda h: -numero(h["titulo"])) if c["ativa"] else []
        meus = [p for p in posts if p.get("campanha") == c["id"]][:6]
        url = f"{SITE}/campanhas/{paginas[c['id']]}/"
        os.makedirs(os.path.join(raiz, paginas[c["id"]]), exist_ok=True)
        open(os.path.join(raiz, paginas[c["id"]], "index.html"), "w", encoding="utf8").write(pagina_campanha(c, eps, hls, resumos, meus, img, url))
        print(f"campanha: campanhas/{paginas[c['id']]}/ ({len(eps)} episódios, {sum(1 for x in eps if x['id'] in resumos)} com resumo)")
    open(os.path.join(raiz, "index.html"), "w", encoding="utf8").write(pagina_lista([c for c in camps if c["id"] in paginas], paginas, img))
    json.dump(paginas, open(os.path.join(raiz, "paginas.json"), "w", encoding="utf8"), ensure_ascii=False)
    open(os.path.join(pasta, "agenda.ics"), "w", encoding="utf8", newline="").write(agenda_ics(camps, paginas, excs))

    # sitemap: o gerar_blog.py escreve; aqui entram as campanhas
    caminho = os.path.join(pasta, "sitemap.xml")
    try:
        sm = open(caminho, encoding="utf8").read()
        sm = re.sub(r"\s*<url><loc>https://papodadorpg\.com\.br/campanhas/[^<]*</loc>.*?</url>", "", sm)
        hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        novas = "".join(f"  <url><loc>{SITE}/campanhas/{s}/</loc><lastmod>{hoje}</lastmod></url>\n" for s in [""] + list(paginas.values()))
        novas = novas.replace("/campanhas//", "/campanhas/")
        open(caminho, "w", encoding="utf8").write(sm.replace("</urlset>", novas + "</urlset>"))
    except FileNotFoundError:
        pass
    print(f"{len(paginas)} campanha(s), agenda.ics com {sum(1 for c in camps if c['ativa'] and c['dados'].get('ref'))} lives")


if __name__ == "__main__":
    main()
