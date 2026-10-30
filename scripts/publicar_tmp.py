#!/usr/bin/env python3
"""Uso único: baixa arquivos do site guardados temporariamente no Supabase e grava no repositório.
Só grava se o conteúdo bater exatamente com o hash esperado. Pode apagar este arquivo depois."""
import hashlib, json, os, sys, urllib.request

URL = "https://oumhibikfxorrknthbqb.supabase.co"
CHAVE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im91bWhpYmlrZnhvcnJrbnRoYnFiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMzODcyNDIsImV4cCI6MjEwODk2MzI0Mn0.JlgqDluN1BEHBAGGpbcVw-wVowlcl_x0EjU2E4e-zns"
ESPERADOS = {
    "admin/index.html": "b616a406932b7ed8d94fc3a79b71c491c946bc89340f0f5a369b3836d652eacb",
    "config.json": "f3e0e90b1dff2d5f5dc8eb0120dc749e75f46816d17a9f116875509aba128c12",
    "supabase/schema.sql": "47ad31304647c65cdf5e969f4014d195cd7cb7bb36ab4fc42a8baae37be2c015",
    "scripts/atualizar_videos.py": "4a2cac445456cc8afe7a3785653e31a5e59aad6fa9577edf8921a0a0d52cdcf1",
    "README.md": "e296715b5492ccae765f05053ab43c1bb165bca7fc5b81d06712a5232fd06f68"
}

pasta = sys.argv[1] if len(sys.argv) > 1 else "."
try:
    req = urllib.request.Request(f"{URL}/rest/v1/tmp_publicar?select=nome,conteudo", headers={"apikey": CHAVE, "Authorization": f"Bearer {CHAVE}"})
    linhas = {x["nome"]: x["conteudo"] for x in json.load(urllib.request.urlopen(req, timeout=30))}
except Exception as e:
    print(f"nada para publicar: {e}")
    sys.exit(0)
for nome, h in ESPERADOS.items():
    dados = linhas.get(nome, "").encode("utf8")
    if hashlib.sha256(dados).hexdigest() != h:
        print(f"{nome}: ausente ou diferente do esperado, ignorado")
        continue
    destino = os.path.join(pasta, nome)
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    open(destino, "wb").write(dados)
    print(f"{nome}: gravado")
