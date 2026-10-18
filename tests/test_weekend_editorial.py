"""Regression: v2.1 weekend labels apply prospectively, not to existing editions."""
import datetime as dt
import importlib.util
import tempfile
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication", ROOT / "tools/prepare_publication.py")
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


class WeekendEditorialVersionTest(unittest.TestCase):
    def test_published_weekend_history_is_not_relabelled(self):
        self.assertEqual(publication.feature_for(dt.date(2026, 10, 17)), "文化与趣味发现")
        self.assertEqual(publication.feature_for(dt.date(2026, 10, 18)), "Weekend Special｜深度专题、东西方哲学、英文精读")

    def test_new_weekend_is_two_independent_features_per_day(self):
        self.assertEqual(publication.feature_for(dt.date(2026, 10, 24)), "Weekend Special｜两篇独立深度专题")
        self.assertEqual(publication.feature_for(dt.date(2026, 10, 25)), "Weekend Special｜深度专题＋英文精读")

    def test_weekday_original_assignments_unchanged(self):
        for day in range(19,24):
            current = dt.date(2026, 10, day)
            self.assertEqual(publication.feature_for(current), publication.FEATURES[current.weekday()])


    def test_future_weekend_requires_two_feature_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            for day in ("2026-10-24", "2026-10-25"):
                folder = Path(tmp) / day
                folder.mkdir()
                story = lambda i, cat: {"id": f"{day}-topic-{i}", "cat": cat,
                                        "title": f"Distinct article {i}", "art": "book"}
                features = [story(1, "专题"), story(2, "专题")]
                base = {"schema": 1, "date": day, "title": "Test only",
                        "category": "专题", "summary": "Synthetic editorial fixture",
                        "stories": features}
                if day.endswith("-24"):
                    base["stories"] += [story(3, "国际")]
                (folder / "stories.json").write_text(json.dumps(base), encoding="utf-8")
                self.assertIsNotNone(publication.read_metadata(folder, "Test only"))
                base["stories"] = features[:1]
                (folder / "stories.json").write_text(json.dumps(base), encoding="utf-8")
                with self.assertRaises(ValueError):
                    publication.read_metadata(folder, "Test only")
                if day.endswith("-25"):
                    base["stories"] = features + [story(3, "专题")]
                    (folder / "stories.json").write_text(json.dumps(base), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        publication.read_metadata(folder, "Test only")



if __name__ == "__main__":
    unittest.main()
