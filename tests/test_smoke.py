   """Smoke tests: the product backlog loads and every requirement is delivered by a Must-have story."""
   import json
   from pathlib import Path

   BACKLOG = Path(__file__).resolve().parents[1] / "tools" / "board" / "backlog.json"


   def load():
       return json.loads(BACKLOG.read_text(encoding="utf-8"))


   def test_backlog_loads():
       data = load()
       assert data["stories"], "backlog has no stories"


   def test_every_requirement_has_a_must_story():
       data = load()
       musts = [s for s in data["stories"] if s["priority"] == "Must"]
       for kind in ("fr", "nfr"):
           for code in data["requirements"][kind]:
               assert any(code in s[kind] for s in musts), f"{code} has no Must story"