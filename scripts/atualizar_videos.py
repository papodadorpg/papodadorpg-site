#!/usr/bin/env python3
"""Gera videos.json do site Papo Dado RPG a partir das abas /streams e /videos do canal.

Uso: python3 -I atualizar_videos.py <pasta_saida>
Escreve <pasta_saida>/videos.json e as capas em <pasta_saida>/img/yt/.
Sai com código 2 (sem escrever nada) se não conseguir ler o canal.

videos.json:
  atualizado  ISO UTC da coleta
  aovivo      [{id, titulo, capa}]                 lives transmitindo agora
  agendadas   [{id, titulo, inicio, capa}]         lives/estreias programadas (inicio em ISO UTC)
  itens       [{id, titulo, data, capa}]           últimos vídeos e lives encerradas, mais novo primeiro
  shorts      [{id, titulo, capa}]                 últimos Shorts (capa vertical)

Também escreve <pasta_saida>/episodios.json:
  atualizado, campanhas: {id_da_campanha: {playlist, episodios: [{id, titulo, duracao}]}},
  highlights: [{id, titulo, capa}]   (playlist "Highlights Campanhas D&D")
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

CANAL = os.environ.get("CANAL", "https://www.youtube.com/@papodadorpg")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
# tz=UTC faz o YouTube escrever "Programado para dd/mm/aaaa, hh:mm" em UTC
COOKIE = "CONSENT=YES+1; SOCS=CAI; PREF=hl=pt-BR&gl=BR&tz=UTC"
AGORA = datetime.now(timezone.utc)

# id da campanha no site -> playlist no canal (em andamento e encerradas)
PLAYLISTS = {
    "strahd": "PLu-hxXZl-KUQqPuVdQ4vg71gQH-ODurab", "vecna": "PLu-hxXZl-KUQ459n-TxtK6seaKrQ6csTM",
    "principes": "PLu-hxXZl-KUSc5pqaRL-ecT4mdzA2TwoD", "saltmarsh": "PLu-hxXZl-KUR73qFR7vgoOk1Lmz_9EMQ0",
    "avernus": "PLu-hxXZl-KUQmEmAz7tpsUA4Cwkn7Hf0E", "restou": "PLHowpbWJeP2Y",
    "mar": "PLu-hxXZl-KUQ2GeNESYZAC_zAfivACpPy", "odisseia": "PLu-hxXZl-KUQPhlqcaUU3HcjBjRBTzlqG",
    "lua": "PLDWqkFFR3FM8", "grande-roda": "PLu-hxXZl-KUQLYts_IURzyVUr7HKIMzln",
    "klataros": "PLu-hxXZl-KUTss1LTl90aY8I-7n5QL1oP", "kraken": "PLu-hxXZl-KUSczalmCKKq5837JH0BL-NL",
    "strahd-benites": "PLu-hxXZl-KUS44rPcrHFtHu9WHxWnfdbF", "tirania": "PLu-hxXZl-KUQvJ3zRPKzgEv5OzbptrdFX",
}
HIGHLIGHTS = "PLGyde_ofvU6A"


def playlists_do_banco(pasta):
    """Campanhas cadastradas no /admin (Supabase) entram na lista; a lista fixa acima é a reserva."""
    try:
        cfg = json.load(open(os.path.join(pasta, "config.json"), encoding="utf8"))
        req = urllib.request.Request(f"{cfg['supabase_url']}/rest/v1/campanhas?select=id,dados",
                                     headers={"apikey": cfg["supabase_anon"], "Authorization": f"Bearer {cfg['supabase_anon']}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            for c in json.load(r):
                pid = (c.get("dados") or {}).get("playlist")
                if pid:
                    PLAYLISTS[c["id"]] = pid
    except Exception as e:
        print(f"campanhas do banco não lidas (usa a lista fixa): {e}", file=sys.stderr)


def capa_da_playlist(cid, pid, pasta):
    """Baixa a capa da playlist para img/pl/<campanha>.webp, só se ainda não existir."""
    destino = os.path.join(pasta, "img", "pl", f"{cid}.webp")
    if os.path.exists(destino):
        return
    try:
        h = baixar(f"https://www.youtube.com/playlist?list={pid}")
        url = re.findall(r'<meta property="og:image" content="([^"]+)"', h)[-1].replace("&amp;", "&")  # a última é a maior
        url = re.sub(r"/(hq|mq|sd)default\.jpg", "/maxresdefault.jpg", url) if "i.ytimg.com/vi/" in url else url
        try:
            bruto = baixar(url, binario=True)
        except Exception:
            bruto = baixar(url.replace("maxresdefault", "hqdefault"), binario=True)
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(bruto)).convert("RGB")
        img.thumbnail((854, 480))
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        img.save(destino, "WEBP", quality=82)
        print(f"capa nova: img/pl/{cid}.webp", file=sys.stderr)
    except Exception as e:
        print(f"capa da playlist {cid} não baixada: {e}", file=sys.stderr)


def baixar(url, binario=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9", "Cookie": COOKIE})
    with urllib.request.urlopen(req, timeout=30) as r:
        dados = r.read()
    return dados if binario else dados.decode("utf8")


def lockups(url):
    html = baixar(url)
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not m:
        return []
    achados = []

    def andar(o):
        if isinstance(o, dict):
            if "lockupViewModel" in o:
                achados.append(o["lockupViewModel"])
            for v in o.values():
                andar(v)
        elif isinstance(o, list):
            for v in o:
                andar(v)

    andar(json.loads(m.group(1)))
    return achados


def textos(o, chave):
    """Todos os valores de strings sob uma chave, em qualquer profundidade."""
    out = []
    if isinstance(o, dict):
        for k, v in o.items():
            if k == chave and isinstance(v, str):
                out.append(v)
            else:
                out += textos(v, chave)
    elif isinstance(o, list):
        for v in o:
            out += textos(v, chave)
    return out


# "há 2 h", "há 14 min", "há 1 dia", "há 3 sem.", "há 2 meses"...: prefixo da unidade -> segundos
UNIDADES = [("seg", 1), ("sem", 604800), ("s", 1), ("h", 3600), ("d", 86400), ("m", 2592000), ("a", 31536000)]


def segundos(qtd, unidade):
    u = unidade.lower()
    if u.startswith("min"):
        return qtd * 60
    for pref, seg in UNIDADES:
        if u.startswith(pref):
            return qtd * seg
    return None


def classificar(lv):
    vid = lv.get("contentId")
    if not vid or lv.get("contentType") not in (None, "LOCKUP_CONTENT_TYPE_VIDEO"):
        return None
    meta = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
    titulo = meta.get("title", {}).get("content", "").strip()
    linhas = textos(meta, "content")
    selos = [t.upper() for t in textos(lv.get("contentImage", {}), "text")]
    junto = " | ".join(linhas)
    item = {"id": vid, "titulo": titulo}

    m = re.search(r"(?:Programad[oa] para|Estreia em|Estreia:?)\s*(\d{2})/(\d{2})/(\d{4}),?\s*(\d{1,2}):(\d{2})", junto)
    if m:
        d, mo, a, h, mi = map(int, m.groups())
        item["tipo"] = "agendada"
        item["inicio"] = datetime(a, mo, d, h, mi, tzinfo=timezone.utc).isoformat()
        return item
    if any(s in ("AO VIVO", "LIVE") for s in selos) or "assistindo agora" in junto:
        item["tipo"] = "aovivo"
        return item
    m = re.search(r"há (\d+)\s*([a-zà-ú]+)", junto, re.I)
    if m and segundos(int(m.group(1)), m.group(2)) is not None:
        item["tipo"] = "passado"
        item["data"] = (AGORA - timedelta(seconds=segundos(int(m.group(1)), m.group(2)))).isoformat(timespec="seconds")
        return item
    return None


def salvar_capa(vid, pasta, grande=False):
    nome = f"img/yt/{vid}-g.webp" if grande else f"img/yt/{vid}.jpg"
    destino = os.path.join(pasta, nome)
    if os.path.exists(destino):
        return nome
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    fontes = ["hq720.jpg", "maxresdefault.jpg", "mqdefault.jpg"] if grande else ["mqdefault.jpg"]
    for f in fontes:
        try:
            bruto = baixar(f"https://i.ytimg.com/vi/{vid}/{f}", binario=True)
        except Exception:
            continue
        if grande:
            from io import BytesIO
            from PIL import Image
            img = Image.open(BytesIO(bruto)).convert("RGB")
            img.thumbnail((720, 405))
            img.save(destino, "WEBP", quality=80)
        else:
            open(destino, "wb").write(bruto)
        return nome
    return None


def shorts(pasta, limite=8):
    html = baixar(f"{CANAL}/shorts")
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not m:
        return []
    achados = []

    def andar(o):
        if isinstance(o, dict):
            if "shortsLockupViewModel" in o:
                achados.append(o["shortsLockupViewModel"])
            for v in o.values():
                andar(v)
        elif isinstance(o, list):
            for v in o:
                andar(v)

    andar(json.loads(m.group(1)))
    out = []
    for sv in achados:
        bruto = json.dumps(sv, ensure_ascii=False)
        vid = (re.findall(r'"videoId": "([^"]+)"', bruto) or [None])[0]
        rotulo = (re.findall(r'"accessibilityText": "([^"]+)"', bruto) or [""])[0]
        titulo = re.sub(r",\s*[\d.,\s\xa0mil]+ visualiza.*$", "", rotulo).strip()
        if not vid or any(x["id"] == vid for x in out):
            continue
        nome = f"img/yt/{vid}-s.webp"
        destino = os.path.join(pasta, nome)
        if not os.path.exists(destino):
            try:
                from io import BytesIO
                from PIL import Image
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                bruto = None
                for f in ("oar2.jpg", "frame0.jpg"):  # oar2 = capa vertical do Short; frame0 pode vir preto
                    try:
                        bruto = baixar(f"https://i.ytimg.com/vi/{vid}/{f}", binario=True)
                        break
                    except Exception:
                        continue
                img = Image.open(BytesIO(bruto)).convert("RGB")
                img.thumbnail((270, 480))
                img.save(destino, "WEBP", quality=80)
            except Exception:
                nome = None
        out.append({"id": vid, "titulo": titulo, "capa": nome})
        if len(out) >= limite:
            break
    return out


def itens_playlist(pid):
    out = []
    for lv in lockups(f"https://www.youtube.com/playlist?list={pid}"):
        if lv.get("contentType") not in (None, "LOCKUP_CONTENT_TYPE_VIDEO") or not lv.get("contentId"):
            continue
        meta = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
        dur = [t for t in textos(lv.get("contentImage", {}), "text") if re.fullmatch(r"\d+(:\d{2}){1,2}", t)]
        out.append({"id": lv["contentId"], "titulo": meta.get("title", {}).get("content", "").strip(), "duracao": dur[0] if dur else ""})
    return out


def episodios(pasta):
    """Lista de episódios de cada playlist de campanha + highlights. Playlist que falhar mantém a lista anterior."""
    caminho = os.path.join(pasta, "episodios.json")
    try:
        antigo = json.load(open(caminho, encoding="utf8"))
    except Exception:
        antigo = {"campanhas": {}, "highlights": []}
    campanhas = {}
    playlists_do_banco(pasta)
    for cid, pid in PLAYLISTS.items():
        capa_da_playlist(cid, pid, pasta)
        try:
            eps = itens_playlist(pid)
        except Exception as e:
            print(f"playlist {cid} falhou: {e}", file=sys.stderr)
            eps = []
        campanhas[cid] = {"playlist": pid, "episodios": eps or antigo.get("campanhas", {}).get(cid, {}).get("episodios", [])}
    try:
        hl = itens_playlist(HIGHLIGHTS)
    except Exception:
        hl = []
    hl = hl or antigo.get("highlights", [])
    for h in hl:
        h["capa"] = salvar_capa(h["id"], pasta)
    if not any(c["episodios"] for c in campanhas.values()):
        print("nenhuma playlist lida; episodios.json não foi alterado", file=sys.stderr)
        return
    with open(caminho, "w", encoding="utf8") as f:
        json.dump({"atualizado": AGORA.isoformat(timespec="seconds"), "campanhas": campanhas, "highlights": hl}, f, ensure_ascii=False, indent=1)


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else "."
    vistos, aovivo, agendadas, passados = set(), [], [], []
    # datas já registradas numa coleta anterior são mais precisas ("há 2 h" vira "há 1 dia" depois)
    anterior = {}
    try:
        for it in json.load(open(os.path.join(pasta, "videos.json"), encoding="utf8")).get("itens", []):
            if it.get("id") and it.get("data"):
                anterior[it["id"]] = it["data"]
    except Exception:
        pass
    for aba in ("streams", "videos"):
        try:
            lista = lockups(f"{CANAL}/{aba}")
        except Exception as e:
            print(f"falhou {aba}: {e}", file=sys.stderr)
            lista = []
        for lv in lista:
            it = classificar(lv)
            if not it or it["id"] in vistos:
                continue
            vistos.add(it["id"])
            {"aovivo": aovivo, "agendada": agendadas, "passado": passados}[it.pop("tipo")].append(it)

    if not passados and not agendadas and not aovivo:
        print("nenhum vídeo lido do canal; videos.json não foi alterado", file=sys.stderr)
        sys.exit(2)

    # agendadas que já passaram há mais de 3 h e nunca começaram ficam de fora
    agendadas = [a for a in agendadas if datetime.fromisoformat(a["inicio"]) > AGORA - timedelta(hours=3)]
    agendadas.sort(key=lambda a: a["inicio"])
    for p in passados:
        if p["id"] in anterior:
            p["data"] = anterior[p["id"]]
    passados.sort(key=lambda p: p["data"], reverse=True)
    itens = passados[:6]

    for it in aovivo + agendadas:
        it["capa"] = salvar_capa(it["id"], pasta, grande=True)
    for i, it in enumerate(itens):
        it["capa"] = salvar_capa(it["id"], pasta)
        if i == 0:  # o último vídeo também pode ir para o herói
            it["capa_grande"] = salvar_capa(it["id"], pasta, grande=True)

    try:
        lista_shorts = shorts(pasta)
    except Exception as e:
        print(f"shorts falhou: {e}", file=sys.stderr)
        lista_shorts = []
    if not lista_shorts:  # mantém os anteriores se a aba falhar
        try:
            lista_shorts = json.load(open(os.path.join(pasta, "videos.json"), encoding="utf8")).get("shorts", [])
        except Exception:
            lista_shorts = []

    saida = {"atualizado": AGORA.isoformat(timespec="seconds"), "aovivo": aovivo, "agendadas": agendadas, "itens": itens, "shorts": lista_shorts}
    with open(os.path.join(pasta, "videos.json"), "w", encoding="utf8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=1)
    episodios(pasta)
    print(json.dumps(saida, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
