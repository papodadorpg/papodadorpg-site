# papodadorpg.com.br

Site do canal Papo Dado RPG. É uma página única (`index.html`) que lê três arquivos de dados:

| Arquivo | O que tem | De onde vem |
|---|---|---|
| `videos.json` | live ao vivo/agendada, últimos vídeos, Shorts | aba do canal no YouTube |
| `episodios.json` | episódios de cada playlist de campanha e highlights | playlists do YouTube |
| `mesas.json` | mesas públicas do Henrique, vagas, datas, preço | MesaQuest |

Esses arquivos são atualizados sozinhos pelo GitHub Actions (`.github/workflows/atualizar-dados.yml`),
a cada 2 horas das 9h às 23h (Brasília). Para rodar na hora: aba **Actions** → *Atualizar dados do site* → **Run workflow**.

## Onde mexer no `index.html`

- **Agenda e campanhas no ar:** lista `LIVES` (horário de referência, intervalo, cor, sinopse, playlist).
- **Campanhas encerradas:** lista `ENCERRADAS`.
- **Dias sem live:** `DIAS_OFF` (sexta = mesas em off).
- **Horário combinado fora do MesaQuest:** `HORA_REAL` dentro de `montarMesaQuest`.
- **Playlists que o robô lê:** `PLAYLISTS` em `scripts/atualizar_videos.py` (inclua a playlist de campanhas novas aqui também).

Capas das playlists ficam em `img/pl/<id da campanha>.webp`.
