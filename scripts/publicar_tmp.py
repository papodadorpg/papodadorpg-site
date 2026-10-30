#!/usr/bin/env python3
"""Uso único: baixa arquivos do site guardados temporariamente no Supabase e grava no repositório.
Só grava se o conteúdo bater exatamente com o hash esperado. Pode apagar este arquivo depois."""
import hashlib, json, os, sys, urllib.request

URL = "https://oumhibikfxorrknthbqb.supabase.co"
CHAVE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im91bWhpYmlrZnhvcnJrbnRoYnFiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTMzODcyNDIsImV4cCI6MjEwODk2MzI0Mn0.JlgqDluN1BEHBAGGpbcVw-wVowlcl_x0EjU2E4e-zns"
ESPERADOS = {
    "index.html": "6a1fe6f7e944192b50946be7c585e39f85e15a2a171d2f6c4d0bf55e97bb208f",
    "admin/index.html": "3c523b02de3672c71ce89d963fb6cdc2b28e27118c4f0307a8af36ed158af1de",
    "README.md": "6146dbeba51c26711ad946b8fb2585cdecaebdd3114aa55eebec4c2d10f4a20b",
    "blog/blog.css": "3a47325e4a41ea07f6b1c0b7526a36428dedc7709a6d982f2ec10ba1cfd09f53",
    "blog/blog.js": "35474fd0f1608b40782bf14c17059ce5e96a16324d5e442d78e847a8fcf7fc3b",
    "scripts/gerar_blog.py": "2cfd554544dc15db1284a5a9c809c0bb7d30ca4b3c895ca2a78f26a9056b6bd6",
    "supabase/blog.sql": "d5f52d488088af3540523d9de1c5372a9b90ea2e3eda52e984b912d2ce4f6d8c",
    "supabase/functions/admins/index.ts": "b400f18515f89891904e154cbaa599bd91a3fdfca8f9798d1d679aae0e94b098"
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
