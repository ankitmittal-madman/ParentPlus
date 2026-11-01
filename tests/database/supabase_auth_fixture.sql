-- ParentPlus local PostgreSQL test fixture.
-- TEST ONLY: Not a real Supabase Auth implementation.
-- Never deploy this file to Supabase or production.

create role anon nologin;
create role authenticated nologin;

create schema auth;

create table auth.users (
  id uuid primary key,
  email text unique
);

create function auth.uid()
returns uuid
language sql
stable
as $$
  select nullif(
    current_setting('request.jwt.claim.sub', true),
    ''
  )::uuid;
$$;

-- This simulates the user ID carried in a Supabase JWT.
-- It is suitable for controlled local testing only.
-- A real Supabase deployment must verify signed JWTs.

insert into auth.users (id, email)
values
  ('11111111-1111-4111-8111-111111111111', 'meera@example.test'),
  ('22222222-2222-4222-8222-222222222222', 'rahul@example.test'),
  ('33333333-3333-4333-8333-333333333333', 'other@example.test');
