from app.services.auth import SupabaseUserAuth


def test_auth_requires_configuration(monkeypatch):
    monkeypatch.delenv("JUST_MAKER_SUPABASE_URL", raising=False)
    monkeypatch.delenv("JUST_MAKER_SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("JUST_MAKER_SUPABASE_ANON_KEY", raising=False)

    auth = SupabaseUserAuth()
    assert auth.configured is False
