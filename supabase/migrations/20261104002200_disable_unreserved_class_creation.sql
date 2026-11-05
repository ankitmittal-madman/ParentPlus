-- Local draft: app roles cannot bypass the unfinished reservation protocol.
begin;
revoke all on function public.create_course(uuid,text,uuid) from public, anon, authenticated;
revoke all on function public.create_batch(uuid,uuid,text,uuid) from public, anon, authenticated;
revoke all on function public.create_course_and_batch(uuid,text,text,uuid) from public, anon, authenticated;
commit;
