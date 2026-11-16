# Protocol fixtures

`fixtures/` is the executable contract of the protocol defined in [docs/protocol.md](../docs/protocol.md). All files are UTF-8 JSON without a BOM.

## Who reads what

| Folder | Content | Read by |
|---|---|---|
| `fixtures/layouts/valid`, `fixtures/layouts/invalid` | Stored layouts and the validation error each invalid one must produce | pytest in `tests/integration`, vitest in `frontend/test` |
| `fixtures/payloads/valid` | A stored layout and the compiled payload (with golden `rev`) | pytest in `tests/integration`, vitest in `frontend/test`, doctest in `esphome/tests` |
| `fixtures/payloads/invalid` | Raw strings sent to `set_layout` and the parse error expected | doctest in `esphome/tests` |
| `fixtures/states` | Home Assistant states and the expected update objects | pytest in `tests/integration` |
| `fixtures/controls` | Control events and the expected service call | pytest in `tests/integration` |
| `fixtures/colors.json` | Background colours and the expected text colour | pytest in `tests/integration`, vitest in `frontend/test`, doctest in `esphome/tests` |

`tests/protocol` checks the fixtures themselves.

## One broken rule per invalid fixture

Each file in `layouts/invalid` takes a valid layout and breaks exactly one rule. Its stem is the expected error code, or the code followed by `-` and a suffix when a code has several cases.

## Canonical revision

```python
hashlib.sha256(json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()[:8]
```

`p` is the payload without its `rev` key. Recompute the golden `rev` of `payloads/valid/*.json` whenever a payload changes.
