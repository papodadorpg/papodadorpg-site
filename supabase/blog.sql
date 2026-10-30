-- Papo Dado RPG · blog (rodar depois do schema.sql). Pode rodar de novo.

-- ============ POSTS ============
create table if not exists public.posts (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' and char_length(slug) <= 80),
  titulo text not null check (char_length(titulo) between 1 and 160),
  resumo text check (char_length(resumo) <= 300),
  capa_url text check (char_length(capa_url) <= 500),
  conteudo text not null default '',
  autor text not null default 'Henrique Müller' check (char_length(autor) <= 80),
  categorias text[] not null default '{}',
  campanha text references public.campanhas(id) on update cascade on delete set null,
  status text not null default 'rascunho' check (status in ('rascunho', 'publicado')),
  publicar_em timestamptz,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index if not exists posts_publicados on public.posts (publicar_em desc) where status = 'publicado';
alter table public.posts enable row level security;

drop policy if exists "todos leem posts publicados" on public.posts;
create policy "todos leem posts publicados" on public.posts for select to anon, authenticated
  using (status = 'publicado' and publicar_em <= now());
drop policy if exists "admins leem todos os posts" on public.posts;
create policy "admins leem todos os posts" on public.posts for select to authenticated using (public.is_admin());
drop policy if exists "admins editam posts" on public.posts;
create policy "admins editam posts" on public.posts for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- histórico (mesma função das campanhas; "registro" = id do post)
drop trigger if exists hist_posts on public.posts;
create trigger hist_posts before insert or update or delete on public.posts for each row execute function public.registrar_historico();
create or replace function public.posts_tocar() returns trigger language plpgsql as $$
begin new.atualizado_em := now(); return new; end $$;
drop trigger if exists posts_atualizado on public.posts;
create trigger posts_atualizado before update on public.posts for each row execute function public.posts_tocar();

-- ============ IMAGENS DO BLOG ============
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('blog', 'blog', true, 5242880, array['image/webp', 'image/jpeg', 'image/png', 'image/gif'])
on conflict (id) do update set public = true, file_size_limit = 5242880, allowed_mime_types = array['image/webp', 'image/jpeg', 'image/png', 'image/gif'];
drop policy if exists "admins enviam imagens do blog" on storage.objects;
create policy "admins enviam imagens do blog" on storage.objects for insert to authenticated with check (bucket_id = 'blog' and public.is_admin());
drop policy if exists "admins trocam imagens do blog" on storage.objects;
create policy "admins trocam imagens do blog" on storage.objects for update to authenticated using (bucket_id = 'blog' and public.is_admin());
drop policy if exists "admins apagam imagens do blog" on storage.objects;
create policy "admins apagam imagens do blog" on storage.objects for delete to authenticated using (bucket_id = 'blog' and public.is_admin());

-- ============ GERAR AS PÁGINAS NO GITHUB ============
-- Ao publicar, o banco pede ao GitHub para rodar o workflow "blog.yml", que cria papodadorpg.com.br/blog/<slug>/.
-- O token do GitHub fica guardado no Vault com o nome "github_token" (cadastrado pelo Henrique).
create extension if not exists pg_net with schema extensions;
create extension if not exists pg_cron;

create table if not exists public.controle (chave text primary key, valor text, quando timestamptz not null default now());
alter table public.controle enable row level security;  -- sem políticas: só funções internas mexem

create or replace function public._disparar_blog() returns text
language plpgsql security definer set search_path = public, extensions as $$
declare
  tok text;
  ultimo timestamptz;
begin
  select decrypted_secret into tok from vault.decrypted_secrets where name = 'github_token' limit 1;
  if tok is null or tok = '' then return 'sem_token'; end if;
  select quando into ultimo from public.controle where chave = 'blog_disparo';
  if ultimo is not null and ultimo > now() - interval '45 seconds' then return 'ja_pedido'; end if;
  insert into public.controle (chave, valor, quando) values ('blog_disparo', 'ok', now())
    on conflict (chave) do update set quando = now();
  perform net.http_post(
    url := 'https://api.github.com/repos/papodadorpg/papodadorpg-site/actions/workflows/blog.yml/dispatches',
    body := jsonb_build_object('ref', 'main'),
    headers := jsonb_build_object(
      'Authorization', 'Bearer ' || tok,
      'Accept', 'application/vnd.github+json',
      'X-GitHub-Api-Version', '2022-11-28',
      'User-Agent', 'papodadorpg-supabase',
      'Content-Type', 'application/json'));
  return 'ok';
end $$;
revoke all on function public._disparar_blog() from public, anon, authenticated;

-- chamado pelo admin depois de salvar um post
create or replace function public.disparar_blog() returns text
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_admin() then raise exception 'sem permissão'; end if;
  return public._disparar_blog();
end $$;
revoke all on function public.disparar_blog() from public, anon;
grant execute on function public.disparar_blog() to authenticated;

-- posts agendados: a cada 10 minutos, se algum acabou de entrar no ar, gera as páginas
create or replace function public.blog_agendados() returns text
language plpgsql security definer set search_path = public as $$
begin
  if exists (select 1 from public.posts where status = 'publicado'
             and publicar_em <= now() and publicar_em > now() - interval '11 minutes'
             and publicar_em > atualizado_em + interval '1 minute') then
    return public._disparar_blog();
  end if;
  return 'nada';
end $$;
revoke all on function public.blog_agendados() from public, anon, authenticated;

select cron.unschedule(jobid) from cron.job where jobname = 'blog-agendados';
select cron.schedule('blog-agendados', '*/10 * * * *', 'select public.blog_agendados()');

-- resultado das últimas chamadas ao GitHub (para conferir): select id, status_code, content from net._http_response order by id desc limit 5;

-- ============ DESTAQUE NA HOME ============
-- 1, 2 ou 3 = vaga fixa na página inicial (1 = card grande). Vazio = entra só se estiver entre os mais recentes.
alter table public.posts add column if not exists destaque smallint check (destaque between 1 and 3);
create unique index if not exists posts_destaque_unico on public.posts (destaque) where destaque is not null;
