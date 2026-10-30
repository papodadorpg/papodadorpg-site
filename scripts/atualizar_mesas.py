#!/usr/bin/env python3
"""Gera mesas.json do site Papo Dado RPG a partir das páginas das mesas no MesaQuest.

Uso: python3 -I atualizar_mesas.py <pasta_saida>
Escreve <pasta_saida>/mesas.json e as capas em <pasta_saida>/img/mq/<slug>.webp.
Sai com código 2 (sem escrever nada) se não conseguir ler nenhuma mesa.

Quais mesas: as do perfil do mestre + as já presentes no mesas.json anterior + SEMENTES.
Entram só as públicas, do mestre, com próxima sessão no futuro (ou começada há menos de 3 h).
"""
import html as htmllib, json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

SITE = "https://mesaquest.com.br"
PERFIL = f"{SITE}/usuario/henrique-muller-papo-dado-rpg-jlg6npor"
MESTRE = "Henrique Müller"
SEMENTES = [
    "odisseia-dos-lordes-dragoes-4x844vrw", "vecna-a-beira-da-ruina-e998t6hx", "fantasmas-de-saltmarsh-507ts3gb",
    "autoral-alem-do-mar-sem-fim-rasf80y8", "a-lua-tortuosa-sbvs0xqf", "maldicao-de-strahd-9ddz7grj",
    "descida-ao-avernus-n9a4dynt", "o-que-restou-de-nos-terra-devastada-w610fhf1", "principes-do-apocalipse-0j4ebd57",
    "phandelver-e-abaixo-o-obelisco-despedacado-9cjfc98a",
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
AGORA = datetime.now(timezone.utc)


def baixar(url, binario=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        dados = r.read()
    return dados if binario else dados.decode("utf8", "replace")


class Descricao(HTMLParser):
    """Texto dos <p> do bloco de descrição (div 'tiptap prose'), ignorando títulos."""

    def __init__(self):
        super().__init__()
        self.dentro = 0  # profundidade de <div> dentro do bloco
        self.em_titulo = False
        self.paragrafos, self.atual = [], []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "") or ""
        if tag == "div" and (self.dentro or "tiptap" in classes):
            self.dentro += 1
        elif self.dentro and tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.em_titulo = True
            self.atual = []
        elif self.dentro and tag in ("p", "li"):
            self.atual = []
        elif self.dentro and tag == "br":
            self.atual.append(" ")

    def handle_endtag(self, tag):
        if not self.dentro:
            return
        if tag == "div":
            self.dentro -= 1
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            # títulos de seção ("Sobre esta Mesa", "Regras da Mesa") ficam de fora; epígrafes entre aspas entram
            t = re.sub(r"\s+", " ", "".join(self.atual)).strip()
            if t and re.search(r"[\"“”«»]|[.!?…]$", t):
                self.paragrafos.append(t)
            self.em_titulo = False
            self.atual = []
        elif tag in ("p", "li"):
            t = re.sub(r"\s+", " ", "".join(self.atual)).strip()
            if t:
                self.paragrafos.append(t)
            self.atual = []

    def handle_data(self, data):
        if self.dentro:
            self.atual.append(data)


def resumir(texto, limite=220):
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) <= limite:
        return texto
    corte = texto[:limite].rsplit(" ", 1)[0].rstrip(" ,;:—-")
    return corte + "…"


def slugs_do_perfil():
    try:
        return re.findall(r'href="/mesas/([a-z0-9-]+)', baixar(PERFIL))
    except Exception as e:
        print(f"perfil não lido: {e}", file=sys.stderr)
        return []


def ler_mesa(slug):
    url = f"{SITE}/mesas/{slug}"
    h = baixar(url)
    blocos = {}
    for m in re.findall(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', h, re.S):
        try:
            d = json.loads(m)
            blocos[d.get("@type")] = d
        except Exception:
            pass
    ev, prod = blocos.get("Event"), blocos.get("Product", {})
    if not ev:
        return None
    organizador = (ev.get("organizer") or {}).get("name", "")
    meta = htmllib.unescape((re.search(r'<meta name="description" content="([^"]*)"', h) or [None, ""])[1]).replace("\xa0", " ")
    partes = [p.strip() for p in meta.split(" | ", 1)[-1].split("•")]
    nivel = next((p for p in partes if re.search(r"níve|Iniciante|Intermedi|Avançad|Veterano", p, re.I)), "")
    preco = next((p for p in partes if p.startswith("R$")), "")
    m = re.search(r"(\d+) vagas? dispon", meta)
    vagas = int(m.group(1)) if m else 0
    privada = '\\"isPrivate\\":true' in h or '"isPrivate":true' in h
    p = Descricao()
    p.feed(h)
    descricao = " ".join(p.paragrafos) or ev.get("description", "")
    capa_url = (re.search(r'<meta property="og:image" content="([^"]+)"', h) or [None, None])[1]
    return {
        "slug": slug,
        "nome": htmllib.unescape(ev.get("name", "")).strip(),
        "url": url,
        "mestre": organizador.split("|")[0].strip(),
        "sistema": (prod.get("brand") or {}).get("name", ""),
        "descricao": resumir(descricao),
        "inicio": ev.get("startDate"),
        "fim": ev.get("endDate"),
        "vagas": vagas,
        "lotada": vagas == 0 or "SoldOut" in (ev.get("offers") or {}).get("availability", ""),
        "preco": preco,
        "nivel": nivel,
        "_privada": privada,
        "_cancelada": "Cancelled" in ev.get("eventStatus", ""),
        "_capa_url": capa_url,
    }


def salvar_capa(item, pasta):
    if not item.get("_capa_url"):
        return None
    nome = f"img/mq/{item['slug']}.webp"
    destino = os.path.join(pasta, nome)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    try:
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(baixar(item["_capa_url"], binario=True))).convert("RGB")
        img.thumbnail((960, 960))
        img.save(destino, "WEBP", quality=80)
        return nome
    except Exception as e:
        print(f"capa de {item['slug']} não baixada: {e}", file=sys.stderr)
        return nome if os.path.exists(destino) else None


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else "."
    anteriores = []
    try:
        anteriores = [x["slug"] for x in json.load(open(os.path.join(pasta, "mesas.json"), encoding="utf8")).get("itens", [])]
    except Exception:
        pass
    slugs = list(dict.fromkeys(slugs_do_perfil() + anteriores + SEMENTES))

    lidas, itens = 0, []
    for slug in slugs:
        try:
            m = ler_mesa(slug)
        except Exception as e:
            print(f"{slug}: {e}", file=sys.stderr)
            continue
        if not m:
            continue
        lidas += 1
        inicio = datetime.fromisoformat(m["inicio"]) if m.get("inicio") else None
        if MESTRE not in m["mestre"] or m["_privada"] or m["_cancelada"] or not inicio or inicio < AGORA - timedelta(hours=3):
            continue
        m["capa"] = salvar_capa(m, pasta)
        itens.append({k: v for k, v in m.items() if not k.startswith("_")})

    if not lidas:
        print("nenhuma mesa lida do MesaQuest; mesas.json não foi alterado", file=sys.stderr)
        sys.exit(2)
    itens.sort(key=lambda x: x["inicio"])
    saida = {"atualizado": AGORA.isoformat(timespec="seconds"), "itens": itens}
    with open(os.path.join(pasta, "mesas.json"), "w", encoding="utf8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    for x in itens:
        print(f"{x['inicio'][:16]}  {x['vagas']} vagas{' (lotada)' if x['lotada'] else ''}  {x['preco']}  {x['nome']}")


if __name__ == "__main__":
    main()
