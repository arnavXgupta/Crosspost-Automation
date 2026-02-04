import json

import unittest

from app.config import Settings
from app.core.orchestrator import Orchestrator
from app.db.repo import Repo
from app.schemas import ScriptCreateRequest


class FakeGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, script, metadata=None, research=""):
        class Obj:
            twitter = {"tweets": ["Hook", "Value", "CTA #a #b"]}

        return Obj()

class TestOrchestratorSmoke(unittest.TestCase):
    def test_generate_preview_persists(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "t.db"
            settings = Settings(
                DATABASE_URL=f"sqlite:///{db_path.as_posix()}",
                GEMINI_API_KEY="test",
            )
            repo = Repo.from_settings(settings)
            payload = ScriptCreateRequest(title="t", content="c")
            job = repo.create_job(payload)

            # Patch generator used inside orchestrator
            import app.core.orchestrator as orch_mod

            orch_mod.AIContentGenerator = lambda api_key, model: FakeGenerator()

            orch = Orchestrator.from_settings(settings, repo=repo)
            out = orch.generate_preview(job.id)
            self.assertIn("twitter", out)

            posts = repo.list_posts(job.id)
            self.assertEqual(len(posts), 1)
            tw = [p for p in posts if p.platform == "twitter"][0]
            self.assertEqual(json.loads(tw.content_json)["tweets"][0], "Hook")


if __name__ == "__main__":
    unittest.main()

