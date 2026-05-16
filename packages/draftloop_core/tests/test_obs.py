import structlog
from draftloop_core.obs import configure_logging, get_logger, traced


def test_get_logger_returns_structlog_logger():
    configure_logging("INFO")
    log = get_logger("draftloop.test")
    assert isinstance(log, structlog.stdlib.BoundLogger) or hasattr(log, "info")


def test_traced_decorator_runs_and_returns_value():
    @traced("test.op")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5


def test_traced_decorator_records_exception():
    @traced("test.op")
    def boom() -> None:
        raise ValueError("nope")

    raised = False
    try:
        boom()
    except ValueError:
        raised = True
    assert raised, "decorator must not swallow exceptions"
