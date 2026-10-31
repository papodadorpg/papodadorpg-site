# papodadorpg.com.br

Site do canal Papo Dado RPG. É uma página única (`index.html`) mais a área restrita `admin/`.

## Admin (papodadorpg.com.br/admin/)

Login só com e-mail e senha (sem Google), em um projeto Supabase (plano gratuito). O cadastro público é desligado:
só entra quem for convidado na aba **Admins** do painel. Quem é convidado vira admin.

- **Acessos:** pessoas, visitas, páginas e cliques por área em 7, 14, 28, 90 dias ou período escolhido.
  O site grava cada visita e clique de forma anônima (código aleatório no navegador, sem nome, e-mail ou IP).
- **Agenda:** criar/editar/encerrar campanhas, mudar horário, cancelar ou remarcar uma data. Vale na hora no site.
  O botão **Atualizar agora** busca na hora as lives e vídeos novos do YouTube (função `disparar_dados` no Supabase).
- **Blog:** editor visual (títulos, listas, imagens, vídeos do YouTube), capa, autor, categorias, campanha relacionada,
  rascunho / publicar agora / agendar. O post aparece no site na hora (página inicial, /blog/ e página da campanha).
- **Admins:** convidar e remover quem entra no admin (Edge Function `admins` no Supabase, em `supabase/functions/admins/`).
- **Histórico:** quem mudou o quê.

O banco está descrito em `supabase/schema.sql` (agenda, acessos, painel) e `supabase/blog.sql` (posts, imagens, agendamento).

### Páginas do blog
Cada post publicado ganha `blog/<endereço>/index.html` (Google e prévia no WhatsApp), gerado por `scripts/gerar_blog.py`
no workflow **Gerar páginas do blog** (`.github/workflows/blog.yml`). Ao publicar, o Supabase pede ao GitHub para rodar esse
workflow usando o token guardado no Vault do Supabase com o nome `github_token` (token "fine-grained" do GitHub só com
*Actions: read and write* neste repositório). Posts agendados são conferidos a cada 10 minutos. Sem token, as páginas
são geradas na atualização diária. Enquanto a página não existe, o `404.html` mostra o post direto do Supabase.
`config.json` tem o endereço do projeto e a chave pública ("anon"), que é feita para ficar no navegador.

## Dados automáticos

| Arquivo | O que tem | De onde vem |
|---|---|---|
| `videos.json` | live ao vivo/agendada, últimos vídeos, Shorts | aba do canal no YouTube |
| `episodios.json` | episódios de cada playlist de campanha e highlights | playlists do YouTube (as cadastradas no admin entram sozinhas) |
| `mesas.json` | mesas públicas do Henrique e da Elisinha, vagas, datas, preço | MesaQuest |

Atualizados pelo GitHub Actions (`.github/workflows/atualizar-dados.yml`) uma vez por dia, às 17h17 (Brasília).
Para rodar na hora: botão **Atualizar agora** na aba Agenda do admin (ou aba **Actions** → *Atualizar dados do site* → **Run workflow**).
O agendamento do GitHub costuma atrasar algumas horas; live criada à tarde pode só aparecer no dia seguinte sem o botão.
Campanha nova com playlist: a capa é baixada para `img/pl/<código>.webp` na próxima atualização (ou envie uma capa pelo admin).

## Reserva no `index.html`

Se o Supabase estiver fora do ar, o site usa as listas `LIVES` e `ENCERRADAS` do próprio `index.html` (a agenda de quando o admin foi ligado).
`DIAS_OFF` (sexta = mesas em off) e `HORA_REAL` (horário combinado fora do MesaQuest) continuam no `index.html`.
