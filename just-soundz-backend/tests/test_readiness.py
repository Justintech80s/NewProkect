from app.services.readiness import ReadinessChecker


class Configured:
    def __init__(self, value):
        self.configured = value


class Router:
    def __init__(self, worker):
        self.worker = worker

    def status(self):
        return {"workers": [{"configured": self.worker}]}


def make_checker(*, database=True, worker=True, artifacts=True, auth=True):
    return ReadinessChecker(
        database=Configured(database),
        router=Router(worker),
        artifact_store=Configured(artifacts),
        user_auth=Configured(auth),
    )


def test_required_database_gap_is_not_ready():
    result = make_checker(database=False, worker=True, artifacts=True, auth=True).check()
    assert result["status"] == "not_ready"
    assert result["ready"] is False


def test_required_worker_gap_is_not_ready():
    result = make_checker(database=True, worker=False, artifacts=True, auth=True).check()
    assert result["status"] == "not_ready"
    assert result["ready"] is False


def test_optional_artifact_gap_is_degraded():
    result = make_checker(database=True, worker=True, artifacts=False, auth=True).check()
    assert result["status"] == "degraded"
    assert result["ready"] is True


def test_fully_configured_is_ready():
    result = make_checker().check()
    assert result["status"] == "ready"
    assert result["ready"] is True
