// Supabase Edge Function "admins": lista, convida e remove quem pode entrar no /admin.
// Só atende quem já é admin (confere o login de quem chama). A chave de serviço fica no servidor do Supabase.
import { createClient } from 'npm:@supabase/supabase-js@2';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const resposta = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), { status, headers: { ...CORS, 'Content-Type': 'application/json' } });

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS });
  const url = Deno.env.get('SUPABASE_URL')!;
  const quem = createClient(url, Deno.env.get('SUPABASE_ANON_KEY')!, {
    global: { headers: { Authorization: req.headers.get('Authorization') ?? '' } },
    auth: { persistSession: false },
  });
  const { data: { user } } = await quem.auth.getUser();
  if (!user) return resposta({ erro: 'Faça login de novo.' }, 401);
  const { data: ehAdmin } = await quem.rpc('is_admin');
  if (!ehAdmin) return resposta({ erro: 'Sem permissão.' }, 403);

  const { acao, email, id } = await req.json().catch(() => ({}));
  const servico = createClient(url, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, { auth: { persistSession: false } });

  if (acao === 'listar') {
    const { data, error } = await servico.auth.admin.listUsers({ perPage: 200 });
    if (error) return resposta({ erro: error.message }, 400);
    const usuarios = data.users
      .map((u) => ({ id: u.id, email: u.email, criado: u.created_at, ultimo_login: u.last_sign_in_at ?? null, ativo: !!u.last_sign_in_at }))
      .sort((a, b) => (a.email ?? '').localeCompare(b.email ?? ''));
    return resposta({ usuarios });
  }
  if (acao === 'convidar') {
    const e = String(email ?? '').trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) return resposta({ erro: 'E-mail inválido.' }, 400);
    const { data, error } = await servico.auth.admin.inviteUserByEmail(e, { redirectTo: 'https://papodadorpg.com.br/admin/' });
    if (error) return resposta({ erro: error.message }, 400);
    return resposta({ ok: true, id: data.user?.id });
  }
  if (acao === 'remover') {
    if (!id) return resposta({ erro: 'Faltou dizer quem remover.' }, 400);
    if (id === user.id) return resposta({ erro: 'Você não pode remover a si mesmo.' }, 400);
    const { error } = await servico.auth.admin.deleteUser(String(id));
    if (error) return resposta({ erro: error.message }, 400);
    return resposta({ ok: true });
  }
  return resposta({ erro: 'Ação desconhecida.' }, 400);
});
