# papodadorpg.com.br

Site do canal Papo Dado RPG. É uma página única (`index.html`) mais a área restrita `admin/`.

## Admin (papodadorpg.com.br/admin/)

Login só com e-mail e senha (sem Google), em um projeto Supabase (plano gratuito). O cadastro público é desligado:
só entra quem for convidado em **Supabase → Authentication → Users → Invite user**. Quem é convidado vira admin.

- **Acessos:** pessoas, visitas, páginas e cliques por área em 7, 14, 28, 90 dias ou período escolhido.
  O site grava cada visita e clique de forma anônima (código aleatório no navegador, sem nome, e-mail ou IP).
- **Agenda:** criar/editar/encerrar campanhas, mudar horário, cancelar ou remarcar uma data. Vale na hora no site.
- **Histórico:** quem mudou o quê.

O banco está descrito em `supabase/schema.sql` (tabelas, regras de segurança e a função do painel).
`config.json` tem o endereço do projeto e a chave pública ("anon"), que é feita para ficar no navegador.

## Dados automáticos

| Arquivo | O que tem | De onde vem |
|---|---|---|
| `videos.json` | live ao vivo/agendada, últimos vídeos, Shorts | aba do canal no YouTube |
| `episodios.json` | episódios de cada playlist de campanha e highlights | playlists do YouTube (as cadastradas no admin entram sozinhas) |
| `mesas.json` | mesas públicas do Henrique e da Elisinha, vagas, datas, preço | MesaQuest |

Atualizados pelo GitHub Actions (`.github/workflows/atualizar-dados.yml`) uma vez por dia, às 17h17 (Brasília).
Para rodar na hora: aba **Actions** → *Atualizar dados do site* → **Run workflow**.
Campanha nova com playlist: a capa é baixada para `img/pl/<código>.webp` na próxima atualização (ou envie uma capa pelo admin).

## Reserva no `index.html`

Se o Supabase estiver fora do ar, o site usa as listas `LIVES` e `ENCERRADAS` do próprio `index.html` (a agenda de quando o admin foi ligado).
`DIAS_OFF` (sexta = mesas em off) e `HORA_REAL` (horário combinado fora do MesaQuest) continuam no `index.html`.
