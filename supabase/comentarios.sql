-- Papo Dado RPG · comentários do blog (rodar depois do blog.sql). Pode rodar de novo.
-- Qualquer leitor comenta com um nome (sem conta). O comentário aparece na hora; no admin dá para responder,
-- ocultar ou apagar. Proteções: limite de comentários seguidos, no máximo 2 links, campo-isca contra robôs (no site).

create table if not exists public.comentarios (
  id uuid primary key default gen_random_uuid(),
  post_id uuid not null references public.posts(id) on delete cascade,
  resposta_de uuid references public.comentarios(id) on delete cascade,
  nome text not null check (char_length(nome) between 2 and 60),
  texto text not null check (char_length(texto) between 2 and 2000),
  do_autor boolean not null default false,
  status text not null default 'publicado' check (status in ('publicado', 'oculto')),
  visitante text check (char_length(visitante) <= 64),
  criado_em timestamptz not null default now()
);
create index if not exists comentarios_post on public.comentarios (post_id, criado_em);
create index if not exists comentarios_recentes on public.comentarios (criado_em desc);
alter table public.comentarios enable row level security;

-- o site (anon) só vê as colunas públicas e só envia nome, texto e a qual comentário responde
revoke all on public.comentarios from anon, authenticated;
grant select (id, post_id, resposta_de, nome, texto, do_autor, criado_em) on public.comentarios to anon;
grant insert (post_id, resposta_de, nome, texto, visitante) on public.comentarios to anon;
grant select, insert, update, delete on public.comentarios to authenticated;

drop policy if exists "todos leem comentarios publicados" on public.comentarios;
create policy "todos leem comentarios publicados" on public.comentarios for select to anon, authenticated
  using (status = 'publicado' and exists (select 1 from public.posts p where p.id = post_id and p.status = 'publicado' and p.publicar_em <= now()));
drop policy if exists "leitores comentam em posts publicados" on public.comentarios;
create policy "leitores comentam em posts publicados" on public.comentarios for insert to anon
  with check (status = 'publicado' and not do_autor
              and exists (select 1 from public.posts p where p.id = post_id and p.status = 'publicado' and p.publicar_em <= now()));
drop policy if exists "admins leem todos os comentarios" on public.comentarios;
create policy "admins leem todos os comentarios" on public.comentarios for select to authenticated using (public.is_admin());
drop policy if exists "admins comentam e moderam" on public.comentarios;
create policy "admins comentam e moderam" on public.comentarios for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- limpeza e anti-spam antes de gravar
create or replace function public.comentarios_antes() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  pai record;
  admin boolean := public.is_admin();
begin
  new.nome := btrim(regexp_replace(new.nome, '\s+', ' ', 'g'));
  new.texto := btrim(regexp_replace(new.texto, '\n{3,}', E'\n\n', 'g'));
  new.criado_em := now();
  if not admin then
    new.do_autor := false;
    new.status := 'publicado';
    if (select count(*) from regexp_matches(new.texto, 'https?://|www\.', 'gi')) > 2 then
      raise exception 'muitos_links' using errcode = 'P0001';
    end if;
    if new.visitante is not null and (select count(*) from public.comentarios
        where visitante = new.visitante and criado_em > now() - interval '2 minutes') >= 3 then
      raise exception 'devagar' using errcode = 'P0001';
    end if;
    if (select count(*) from public.comentarios where post_id = new.post_id and criado_em > now() - interval '10 minutes') >= 30 then
      raise exception 'devagar' using errcode = 'P0001';
    end if;
  end if;
  -- respostas ficam em um nível só (resposta de resposta vira resposta do comentário original)
  if new.resposta_de is not null then
    select post_id, resposta_de into pai from public.comentarios where id = new.resposta_de;
    if not found or pai.post_id <> new.post_id then raise exception 'resposta_invalida' using errcode = 'P0001'; end if;
    if pai.resposta_de is not null then new.resposta_de := pai.resposta_de; end if;
  end if;
  return new;
end $$;
drop trigger if exists comentarios_antes on public.comentarios;
create trigger comentarios_antes before insert on public.comentarios for each row execute function public.comentarios_antes();
