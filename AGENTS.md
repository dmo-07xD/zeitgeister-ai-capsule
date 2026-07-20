# Zeitgeister project rules

- Use Python's standard library only; do not add package dependencies.
- Canonical JSON must use sorted keys, compact separators, UTF-8, and `allow_nan=False`.
- Keep signing keys local. Never print, add, or commit a key. `.gitignore` protects common local-key paths.
- State the threat model accurately: HMAC proves possession of the local shared key and detects changes; it does not encrypt, make data immutable, or verify independent/third-party authorship.
- Preserve `Zeitgeister logo.png` and `Zeitgeister thumbnail.png`.

Verification commands:

```sh
python3 -m unittest discover -s tests -v
python3 demo.py --guided
python3 -m zeitgeister --help
```
