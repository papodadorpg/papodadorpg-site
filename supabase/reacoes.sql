-- Papo Dado RPG · reações dos posts do blog (só positivas). Rodar depois do blog.sql. Pode rodar de novo.
-- Cada leitor marca quantas reações quiser em cada post (uma de cada tipo) e pode desmarcar.
-- O leitor é identificado pelo mesmo código aleatório do navegador usado na contagem de acessos (sem nome, e-mail ou IP).

create table if not exists public.reacoes (
  post_id uuid not null references public.posts(id) on delete cascade,
  tipo text not null check (tipo in ('critico', 'inspirou', 'util', 'divertido')),
  visitante text not null check (char_length(visitante) between 8 and 64),
  criado_em timestamptz not null default now(),
  primary key (post_id, tipo, visitante)
);
create index if not exists reacoes_visitante on public.reacoes (visitante, criado_em desc);
alter table public.reacoes enable row level security;
revoke all on public.reacoes from anon, authenticated;
grant select on public.reacoes to authenticated;
drop policy if exists "admins leem reacoes" on public.reacoes;
create policy "admins leem reacoes" on public.reacoes for select to authenticated using (public.is_admin());

-- contagem de um post e quais reações este visitante já marcou
create or replace function public.reacoes_do_post(p_post uuid, p_visitante text default null) returns jsonb
language sql stable security definer set search_path = public as $$
  select jsonb_build_object(
    'contagem', coalesce((select jsonb_object_agg(tipo, n) from (select tipo, count(*) as n from public.reacoes where post_id = p_post group by tipo) t), '{}'::jsonb),
    'minhas', coalesce((select jsonb_agg(tipo) from public.reacoes where post_id = p_post and visitante = p_visitante), '[]'::jsonb));
$$;
revoke all on function public.reacoes_do_post(uuid, text) from public;
grant execute on function public.reacoes_do_post(uuid, text) to anon, authenticated;

-- marca ou desmarca uma reação e devolve a contagem atualizada
create or replace function public.reagir(p_post uuid, p_tipo text, p_visitante text) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  if p_visitante is null or char_length(p_visitante) < 8 or char_length(p_visitante) > 64 then
    raise exception 'visitante_invalido' using errcode = 'P0001';
  end if;
  if not exists (select 1 from public.posts where id = p_post and status = 'publicado' and publicar_em <= now()) then
    raise exception 'post_invalido' using errcode = 'P0001';
  end if;
  if (select count(*) from public.reacoes where visitante = p_visitante and criado_em > now() - interval '1 minute') >= 20 then
    raise exception 'devagar' using errcode = 'P0001';
  end if;
  if exists (select 1 from public.reacoes where post_id = p_post and tipo = p_tipo and visitante = p_visitante) then
    delete from public.reacoes where post_id = p_post and tipo = p_tipo and visitante = p_visitante;
  else
    insert into public.reacoes (post_id, tipo, visitante) values (p_post, p_tipo, p_visitante);
  end if;
  return public.reacoes_do_post(p_post, p_visitante);
end $$;
revoke all on function public.reagir(uuid, text, text) from public;
grant execute on function public.reagir(uuid, text, text) to anon, authenticated;
