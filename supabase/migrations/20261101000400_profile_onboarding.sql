-- ParentPlus M2: Profile onboarding
-- DRAFT ONLY. Test before deployment.

-- Allow authentication before display-name collection.
alter table public.profiles
  alter column display_name drop not null;

-- Preserve non-empty names when supplied.
alter table public.profiles
  drop constraint if exists profiles_display_name_check;

alter table public.profiles
  add constraint profiles_display_name_check
  check (
    display_name is null
    or length(trim(display_name)) > 0
  );

-- Create a profile for each new authentication user.
create or replace function public.handle_new_auth_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id)
  values (new.id)
  on conflict (id) do nothing;

  return new;
end;
$$;

revoke all on function public.handle_new_auth_user() from public;
revoke all on function public.handle_new_auth_user() from anon;
revoke all on function public.handle_new_auth_user() from authenticated;

create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_auth_user();

-- Backfill profiles for existing users.
insert into public.profiles (id)
select id from auth.users
on conflict (id) do nothing;

-- SECURITY REVIEW REQUIRED:
-- Verify trigger ownership, auth.users permissions,
-- profile deletion behavior, and onboarding failure handling.
