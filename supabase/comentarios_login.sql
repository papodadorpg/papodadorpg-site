-- Papo Dado RPG · comentários: login com Google e aviso por e-mail (rodar depois do comentarios.sql). Pode rodar de novo.

-- ============ 1. SÓ CONVIDADO VIRA ADMIN ============
-- Com o login de leitores (Google), nem todo usuário do Auth é admin: só quem foi convidado pela aba Admins.
create or replace function public.novo_admin() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.invited_at is not null then
    insert into public.admins (user_id, email) values (new.id, new.email) on conflict do nothing;
  end if;
  return new;
end $$;

-- ============ 2. COMENTÁRIO DE QUEM ENTROU COM GOOGLE ============
alter table public.comentarios add column if not exists user_id uuid references auth.users(id) on delete set null;
alter table public.comentarios add column if not exists avatar_url text check (char_length(avatar_url) <= 500);
grant select (avatar_url) on public.comentarios to anon;

drop policy if exists "leitores logados comentam" on public.comentarios;
create policy "leitores logados comentam" on public.comentarios for insert to authenticated
  with check (user_id = auth.uid() and status = 'publicado' and not do_autor
              and exists (select 1 from public.posts p where p.id = post_id and p.status = 'publicado' and p.publicar_em <= now()));

-- limpeza e anti-spam; nome e foto de quem está logado vêm da conta Google, não do formulário
create or replace function public.comentarios_antes() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  pai record;
  admin boolean := public.is_admin();
  meta jsonb := coalesce(auth.jwt() -> 'user_metadata', '{}'::jsonb);
begin
  new.criado_em := now();
  if not admin then
    new.do_autor := false;
    new.status := 'publicado';
    if auth.uid() is not null then
      new.user_id := auth.uid();
      new.nome := coalesce(nullif(btrim(meta ->> 'full_name'), ''), nullif(btrim(meta ->> 'name'), ''), new.nome);
      new.avatar_url := left(coalesce(meta ->> 'avatar_url', meta ->> 'picture'), 500);
    else
      new.user_id := null;
      new.avatar_url := null;
    end if;
  end if;
  new.nome := left(btrim(regexp_replace(new.nome, '\s+', ' ', 'g')), 60);
  new.texto := btrim(regexp_replace(new.texto, '\n{3,}', E'\n\n', 'g'));
  if not admin then
    if (select count(*) from regexp_matches(new.texto, 'https?://|www\.', 'gi')) > 2 then
      raise exception 'muitos_links' using errcode = 'P0001';
    end if;
    if (select count(*) from public.comentarios
        where ((new.visitante is not null and visitante = new.visitante) or (new.user_id is not null and user_id = new.user_id))
          and criado_em > now() - interval '2 minutes') >= 3 then
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

-- ============ 3. AVISO POR E-MAIL ============
-- O endereço do script do Google (Apps Script "Aviso de comentários - Papo Dado Blog", conta papodadorpg@gmail.com)
-- fica na tabela controle, chave 'aviso_comentario_url'. O script manda um e-mail para a própria conta.
create or replace function public.comentarios_aviso() returns trigger
language plpgsql security definer set search_path = public, extensions as $$
declare
  url text;
  p record;
begin
  if new.do_autor then return new; end if;
  select valor into url from public.controle where chave = 'aviso_comentario_url';
  if url is null or url = '' then return new; end if;
  select titulo, slug into p from public.posts where id = new.post_id;
  perform net.http_post(
    url := url,
    body := jsonb_build_object('post', p.titulo, 'nome', new.nome, 'texto', new.texto,
                               'resposta', new.resposta_de is not null, 'google', new.user_id is not null,
                               'link', 'https://papodadorpg.com.br/blog/' || p.slug || '/#c-' || new.id),
    headers := '{"Content-Type": "application/json"}'::jsonb);
  return new;
exception when others then
  return new;  -- o aviso nunca impede o comentário
end $$;
revoke all on function public.comentarios_aviso() from public, anon, authenticated;
drop trigger if exists comentarios_aviso on public.comentarios;
create trigger comentarios_aviso after insert on public.comentarios for each row execute function public.comentarios_aviso();
