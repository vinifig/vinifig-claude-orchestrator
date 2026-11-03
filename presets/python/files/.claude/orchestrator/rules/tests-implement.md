# Python rules for tests-implement

- pytest; one file: `uv run pytest -q tests/<path>.py -k <name>`.
- Fixtures in `conftest.py` next to the tests that use them; fakes for ports instead of mocks when a port exists.
- `pytest.mark.parametrize` for rule tables; injected clock or freezegun for time; `tmp_path` for files.
- Never `pytest.mark.skip`/`xfail` to get green; never loosen `approx` tolerances to pass.
