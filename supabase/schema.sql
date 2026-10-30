-- Papo Dado RPG · banco do site (Supabase)
-- Rodar inteiro no SQL Editor do projeto. Pode rodar de novo: tudo é "if not exists" / "or replace".

-- ============ ADMINS ============
-- Todo usuário do Auth é admin: o cadastro público fica desligado e só entra quem for convidado.
create table if not exists public.admins (
  user_id uuid primary key references auth.users(id) on delete cascade,
  email text,
  nome text,
  criado_em timestamptz not null default now()
);
alter table public.admins enable row level security;

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid());
$$;

create or replace function public.novo_admin() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.admins (user_id, email) values (new.id, new.email) on conflict do nothing;
  return new;
end $$;
drop trigger if exists ao_criar_usuario on auth.users;
create trigger ao_criar_usuario after insert on auth.users for each row execute function public.novo_admin();
insert into public.admins (user_id, email) select id, email from auth.users on conflict do nothing;

drop policy if exists "admins leem admins" on public.admins;
create policy "admins leem admins" on public.admins for select to authenticated using (public.is_admin());
drop policy if exists "admin edita o próprio nome" on public.admins;
create policy "admin edita o próprio nome" on public.admins for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

-- ============ CAMPANHAS E EXCEÇÕES DA AGENDA ============
-- dados: o mesmo formato das listas LIVES/ENCERRADAS do site (nome, ref, cada, cor, sistema, mestre, sinopse, sobre, playlist, capa_url...)
create table if not exists public.campanhas (
  id text primary key check (id ~ '^[a-z0-9-]{2,40}$'),
  ativa boolean not null default true,      -- true = no ar no canal; false = encerrada
  ordem int not null default 0,
  dados jsonb not null default '{}'::jsonb,
  atualizado_em timestamptz not null default now()
);
alter table public.campanhas enable row level security;

-- data = dia (Brasília) da sessão normal que muda; remarcada leva para novo_inicio ("AAAA-MM-DDTHH:MM", Brasília)
create table if not exists public.excecoes (
  id bigint generated always as identity primary key,
  campanha text not null references public.campanhas(id) on update cascade on delete cascade,
  data date not null,
  acao text not null check (acao in ('cancelada', 'remarcada')),
  novo_inicio text check (novo_inicio is null or novo_inicio ~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$'),
  nota text check (char_length(nota) <= 200),
  criado_em timestamptz not null default now(),
  unique (campanha, data),
  check (acao = 'cancelada' or novo_inicio is not null)
);
alter table public.excecoes enable row level security;

drop policy if exists "todos leem campanhas" on public.campanhas;
create policy "todos leem campanhas" on public.campanhas for select to anon, authenticated using (true);
drop policy if exists "admins editam campanhas" on public.campanhas;
create policy "admins editam campanhas" on public.campanhas for all to authenticated using (public.is_admin()) with check (public.is_admin());

drop policy if exists "todos leem excecoes" on public.excecoes;
create policy "todos leem excecoes" on public.excecoes for select to anon, authenticated using (true);
drop policy if exists "admins editam excecoes" on public.excecoes;
create policy "admins editam excecoes" on public.excecoes for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- ============ HISTÓRICO DE ALTERAÇÕES ============
create table if not exists public.historico (
  id bigint generated always as identity primary key,
  quando timestamptz not null default now(),
  email text,
  tabela text not null,
  acao text not null,
  registro text,
  antes jsonb,
  depois jsonb
);
alter table public.historico enable row level security;
drop policy if exists "admins leem historico" on public.historico;
create policy "admins leem historico" on public.historico for select to authenticated using (public.is_admin());

create or replace function public.registrar_historico() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  reg jsonb := to_jsonb(coalesce(new, old));
begin
  insert into public.historico (email, tabela, acao, registro, antes, depois)
  values (coalesce(auth.jwt() ->> 'email', 'sistema'), tg_table_name, lower(tg_op),
          coalesce(reg ->> 'campanha', reg ->> 'id'),
          case when tg_op <> 'INSERT' then to_jsonb(old) end,
          case when tg_op <> 'DELETE' then to_jsonb(new) end);
  if tg_op = 'UPDATE' and tg_table_name = 'campanhas' then new.atualizado_em := now(); end if;
  return coalesce(new, old);
end $$;
drop trigger if exists hist_campanhas on public.campanhas;
create trigger hist_campanhas before insert or update or delete on public.campanhas for each row execute function public.registrar_historico();
drop trigger if exists hist_excecoes on public.excecoes;
create trigger hist_excecoes after insert or update or delete on public.excecoes for each row execute function public.registrar_historico();

-- ============ CAPAS (upload pelo admin) ============
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('capas', 'capas', true, 2097152, array['image/webp', 'image/jpeg', 'image/png'])
on conflict (id) do update set public = true, file_size_limit = 2097152, allowed_mime_types = array['image/webp', 'image/jpeg', 'image/png'];
drop policy if exists "admins enviam capas" on storage.objects;
create policy "admins enviam capas" on storage.objects for insert to authenticated with check (bucket_id = 'capas' and public.is_admin());
drop policy if exists "admins trocam capas" on storage.objects;
create policy "admins trocam capas" on storage.objects for update to authenticated using (bucket_id = 'capas' and public.is_admin());
drop policy if exists "admins apagam capas" on storage.objects;
create policy "admins apagam capas" on storage.objects for delete to authenticated using (bucket_id = 'capas' and public.is_admin());

-- ============ ACESSOS ============
-- visitante: código aleatório guardado no navegador (sem nome, e-mail ou IP); visita: sessão de navegação (30 min sem atividade encerra)
create table if not exists public.eventos (
  id bigint generated always as identity primary key,
  criado_em timestamptz not null default now(),
  visitante uuid not null,
  visita uuid not null,
  tipo text not null check (tipo in ('pagina', 'clique')),
  pagina text check (char_length(pagina) <= 120),
  area text check (char_length(area) <= 40),
  alvo text check (char_length(alvo) <= 120),
  destino text check (char_length(destino) <= 120),
  origem text check (char_length(origem) <= 80),
  aparelho text check (aparelho in ('celular', 'tablet', 'computador'))
);
create index if not exists eventos_quando on public.eventos (criado_em);
create index if not exists eventos_tipo_quando on public.eventos (tipo, criado_em);
alter table public.eventos enable row level security;

-- qualquer visitante só consegue INSERIR (e só estas colunas); ninguém de fora lê
revoke all on public.eventos from anon, authenticated;
grant insert (visitante, visita, tipo, pagina, area, alvo, destino, origem, aparelho) on public.eventos to anon, authenticated;
drop policy if exists "site registra eventos" on public.eventos;
create policy "site registra eventos" on public.eventos for insert to anon, authenticated with check (true);
drop policy if exists "admins leem eventos" on public.eventos;
grant select on public.eventos to authenticated;
create policy "admins leem eventos" on public.eventos for select to authenticated using (public.is_admin());

-- Painel: de p_inicio a p_fim (datas de Brasília, inclusivas). Compara com o período anterior de mesmo tamanho.
create or replace function public.painel(p_inicio date, p_fim date) returns jsonb
language plpgsql stable security definer set search_path = public as $$
declare
  tz constant text := 'America/Sao_Paulo';
  ini timestamptz := (p_inicio::timestamp) at time zone tz;
  fim timestamptz := ((p_fim + 1)::timestamp) at time zone tz;
  dur interval := fim - ini;
  r jsonb;
begin
  if not public.is_admin() then raise exception 'sem permissão'; end if;
  if p_fim < p_inicio or p_fim - p_inicio > 400 then raise exception 'período inválido'; end if;

  with ev as (select * from eventos where criado_em >= ini and criado_em < fim),
  ant as (select * from eventos where criado_em >= ini - dur and criado_em < ini),
  dias as (select generate_series(p_inicio, p_fim, interval '1 day')::date as dia),
  por_dia as (
    select (criado_em at time zone tz)::date as dia, count(distinct visitante) as pessoas, count(distinct visita) as visitas,
           count(*) filter (where tipo = 'pagina') as paginas, count(*) filter (where tipo = 'clique') as cliques
    from ev group by 1
  ),
  areas as (
    select area, count(*) as cliques, count(distinct visitante) as pessoas
    from ev where tipo = 'clique' and area is not null group by area
  ),
  alvos as (
    select area, alvo, cliques from (
      select area, alvo, count(*) as cliques, row_number() over (partition by area order by count(*) desc) as n
      from ev where tipo = 'clique' and alvo is not null group by area, alvo
    ) x where n <= 8
  ),
  origens as (
    select coalesce(origem, 'direto') as origem, count(distinct visita) as visitas
    from (select distinct on (visita) visita, origem from ev where tipo = 'pagina' order by visita, criado_em) p
    group by 1
  ),
  aparelhos as (
    select coalesce(aparelho, '?') as aparelho, count(distinct visitante) as pessoas from ev group by 1
  ),
  paginas as (
    select pagina, count(*) as vistas, count(distinct visitante) as pessoas
    from ev where tipo = 'pagina' group by pagina
  )
  select jsonb_build_object(
    'periodo', jsonb_build_object('inicio', p_inicio, 'fim', p_fim),
    'totais', (select jsonb_build_object('pessoas', count(distinct visitante), 'visitas', count(distinct visita),
                 'paginas', count(*) filter (where tipo = 'pagina'), 'cliques', count(*) filter (where tipo = 'clique')) from ev),
    'anterior', (select jsonb_build_object('pessoas', count(distinct visitante), 'visitas', count(distinct visita),
                 'paginas', count(*) filter (where tipo = 'pagina'), 'cliques', count(*) filter (where tipo = 'clique')) from ant),
    'por_dia', (select coalesce(jsonb_agg(jsonb_build_object('dia', d.dia, 'pessoas', coalesce(p.pessoas, 0), 'visitas', coalesce(p.visitas, 0),
                 'paginas', coalesce(p.paginas, 0), 'cliques', coalesce(p.cliques, 0)) order by d.dia), '[]')
                from dias d left join por_dia p using (dia)),
    'areas', (select coalesce(jsonb_agg(to_jsonb(a) order by a.cliques desc), '[]') from areas a),
    'alvos', (select coalesce(jsonb_agg(to_jsonb(a) order by a.area, a.cliques desc), '[]') from alvos a),
    'origens', (select coalesce(jsonb_agg(to_jsonb(o) order by o.visitas desc), '[]') from (select * from origens order by visitas desc limit 12) o),
    'aparelhos', (select coalesce(jsonb_agg(to_jsonb(a) order by a.pessoas desc), '[]') from aparelhos a),
    'paginas', (select coalesce(jsonb_agg(to_jsonb(p) order by p.vistas desc), '[]') from (select * from paginas order by vistas desc limit 15) p),
    'primeiro_evento', (select min(criado_em) from eventos)
  ) into r;
  return r;
end $$;
revoke all on function public.painel(date, date) from public, anon;
grant execute on function public.painel(date, date) to authenticated;

-- Limpeza: eventos com mais de 2 anos (rodar quando quiser: select public.limpar_eventos();)
create or replace function public.limpar_eventos() returns bigint
language sql security definer set search_path = public as $$
  with x as (delete from eventos where criado_em < now() - interval '2 years' returning 1) select count(*) from x;
$$;
revoke all on function public.limpar_eventos() from public, anon, authenticated;
