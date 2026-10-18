"""Regression tests use isolated synthetic editions; never publish their content."""
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publication', REPO / 'tools/prepare_publication.py')
publication = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publication)


class PublicationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ('index.html', 'archive.html', 'assets/app.js'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, path)
        # Isolated fixed data: later real publications must not change test expectations.
        self.old_catalog = {'schema': 1, 'issues': []}
        self.items = []
        for date, complete in [('2026-10-16', False), ('2026-10-14', True)]:
            item = self.stage(date, complete=complete)
            if complete:
                self.items.append(item)
            self.old_catalog['issues'].append({
                'date': date, 'title': item['title'], 'feature': item['feature'],
                'category': publication.CATEGORIES[publication.dt.date.fromisoformat(date).weekday()],
                'summary': 'TEST ONLY legacy summary', 'html': 'issues/' + date + '/index.html',
                'pdf_full': 'issues/' + date + '/完整版.pdf' if complete else None,
                'pdf_podcast': 'issues/' + date + '/播客版.pdf' if complete else None,
                'stories': [{'id': date + '-1', 'cat': '科技', 'title': 'TEST ONLY legacy story', 'art': 'ai'}],
            })
        (self.root / 'site').mkdir()
        (self.root / 'site/catalog.json').write_text(json.dumps(self.old_catalog))
        (self.root / 'issues.json').write_text(json.dumps({'version': 1, 'issues': self.items}))
        self.day = '2026-10-18'  # A Sunday: synthetic Weekend Special, not real news.
        self.item = self.stage(self.day)
        self.metadata = {
            'schema': 1, 'date': self.day, 'title': self.item['title'],
            'category': '专题', 'summary': 'TEST ONLY — synthetic editorial metadata.',
            'stories': [
                {'id': self.day + '-part-' + str(i), 'cat': '专题',
                 'title': 'TEST ONLY — section ' + str(i), 'art': 'book'}
                for i in range(1, 4)
            ],
        }
        self.items.append(self.item)
        self.write_metadata()
        self.before = self.snapshot()

    def stage(self, date, complete=True):
        folder = self.root / 'issues' / date
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'index.html').write_text('<html><body>TEST ONLY: no news extraction</body></html>')
        if complete:
            # Structural gate fixture, not a visually QA-approved or deliverable PDF.
            for name in ('完整版.pdf', '播客版.pdf'):
                (folder / name).write_bytes(b'%PDF-1.4\nTEST ONLY\n%%EOF\n')
        day = publication.dt.date.fromisoformat(date)
        return {'date': date, 'title': 'TEST ONLY — ' + date,
                'feature': publication.FEATURES[day.weekday()],
                'cutoff': date + 'T10:00:00+08:00'}

    def write_metadata(self):
        (self.root / 'issues' / self.day / 'stories.json').write_text(
            json.dumps(self.metadata, ensure_ascii=False), encoding='utf-8')

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def assert_blocked(self):
        before = self.snapshot()
        with self.assertRaises((ValueError, TypeError)):
            publication.build(self.root, self.items)
        self.assertEqual(before, self.snapshot(), 'Failure must not write either manifest or content')

    def test_new_sunday_metadata_reaches_catalog_preserving_history_and_ui(self):
        publication.build(self.root, self.items)
        catalog = json.loads((self.root / 'site/catalog.json').read_text())
        latest = catalog['issues'][0]
        self.assertEqual(latest['date'], self.day)
        self.assertEqual(latest['stories'], self.metadata['stories'])
        self.assertEqual(latest['summary'], self.metadata['summary'])
        self.assertTrue(latest['feature'].startswith('Weekend Special'))
        self.assertTrue(latest['pdf_full'] and latest['pdf_podcast'])
        self.assertEqual(catalog['issues'][1:], self.old_catalog['issues'])
        self.assertEqual(len(json.loads((self.root / 'issues.json').read_text())['issues']), 2)
        after = self.snapshot()
        for name, content in self.before.items():
            if name not in ('issues.json', 'site/catalog.json'):
                self.assertEqual(content, after[name], name)

    def test_repeat_is_byte_identical(self):
        publication.build(self.root, self.items)
        first = self.snapshot()
        publication.build(self.root, self.items)
        self.assertEqual(first, self.snapshot())

    def test_missing_metadata_blocks_new_issue(self):
        (self.root / 'issues' / self.day / 'stories.json').unlink()
        self.assert_blocked()

    def test_invalid_metadata_blocks_without_writes(self):
        mutations = [
            lambda m: m.update(date='2026-10-17'),
            lambda m: m.update(title='different title'),
            lambda m: m.update(schema=True),
            lambda m: m.update(stories=[]),
            lambda m: m.update(stories={}),
            lambda m: m.update(summary=' '),
            lambda m: m.update(category='unsupported'),
            lambda m: m.update(private_notes='must never enter public data'),
            lambda m: m['stories'].append(copy.deepcopy(m['stories'][0])),
            lambda m: m['stories'][0].update(id='2026-10-14-1'),
            lambda m: m['stories'][0].update(cat='unsupported'),
            lambda m: m['stories'][0].update(art='unsupported'),
            lambda m: m['stories'][0].update(title=''),
            lambda m: m['stories'][0].update(title=123),
            lambda m: m['stories'][0].update(private_notes='forbidden'),
        ]
        original = copy.deepcopy(self.metadata)
        for mutate in mutations:
            self.metadata = copy.deepcopy(original)
            mutate(self.metadata)
            self.write_metadata()
            with self.subTest(metadata=self.metadata):
                self.assert_blocked()

    def test_malformed_json_blocks_without_writes(self):
        (self.root / 'issues' / self.day / 'stories.json').write_text('{broken')
        self.assert_blocked()

    def test_symlink_metadata_blocks(self):
        path = self.root / 'issues' / self.day / 'stories.json'
        data = path.read_bytes()
        path.unlink()
        target = self.root / 'other.json'
        target.write_bytes(data)
        path.symlink_to(target)
        self.assert_blocked()

    def test_missing_or_invalid_pdf_blocks_both_manifests(self):
        for name in ('完整版.pdf', '播客版.pdf'):
            path = self.root / 'issues' / self.day / name
            original = path.read_bytes()
            for data in (None, b'', b'<html>404</html>', b'%PDF-1.4 without EOF'):
                if data is None:
                    path.unlink()
                else:
                    path.write_bytes(data)
                with self.subTest(name=name, data=data):
                    self.assert_blocked()
            path.write_bytes(original)

    def test_missing_historical_html_only_issue_cannot_drop_history(self):
        (self.root / 'issues/2026-10-16/index.html').unlink()
        self.assert_blocked()

    def test_invalid_historical_html_cannot_drop_history(self):
        (self.root / 'issues/2026-10-16/index.html').write_text('incomplete')
        self.assert_blocked()

    def test_duplicate_catalog_dates_block(self):
        self.old_catalog['issues'].append(copy.deepcopy(self.old_catalog['issues'][0]))
        (self.root / 'site/catalog.json').write_text(json.dumps(self.old_catalog))
        self.assert_blocked()

    def test_unrequested_new_html_only_folder_cannot_bypass_complete_gate(self):
        self.stage('2026-10-17', complete=False)
        self.assert_blocked()

    def test_legacy_rerun_needs_no_sidecar_and_does_not_promote_html_only(self):
        shutil.rmtree(self.root / 'issues' / self.day)
        publication.build(self.root, self.items[:-1])
        after = json.loads((self.root / 'site/catalog.json').read_text())
        self.assertEqual(after['issues'], self.old_catalog['issues'])
        self.assertEqual(json.loads((self.root / 'issues.json').read_text())['issues'], self.items[:-1])

    def test_older_backfill_does_not_move_latest_backwards(self):
        old = self.stage('2026-10-13')
        metadata = copy.deepcopy(self.metadata)
        metadata.update(date=old['date'], title=old['title'], category='科技')
        for story in metadata['stories']:
            story['id'] = story['id'].replace(self.day, old['date'])
        (self.root / 'issues' / old['date'] / 'stories.json').write_text(json.dumps(metadata))
        publication.build(self.root, self.items + [old])
        issues = json.loads((self.root / 'site/catalog.json').read_text())['issues']
        self.assertEqual([i['date'] for i in issues], [self.day, '2026-10-16', '2026-10-14', '2026-10-13'])

    def test_story_id_changes_to_published_issue_block(self):
        publication.build(self.root, self.items)
        self.metadata['stories'][0]['id'] += '-changed'
        self.write_metadata()
        self.assert_blocked()

    def test_cli_and_approved_app_render_generated_data(self):
        result = subprocess.run([
            sys.executable, str(REPO / 'tools/prepare_publication.py'), '--root', str(self.root),
            '--date', self.day, '--title', self.item['title'], '--cutoff', self.item['cutoff'],
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        node = subprocess.run([
            'node', str(REPO / 'tests/check_catalog_ui.cjs'),
            str(self.root / 'site/catalog.json'), str(self.root / 'assets/app.js'),
        ], capture_output=True, text=True)
        self.assertEqual(node.returncode, 0, node.stderr)


if __name__ == '__main__':
    unittest.main()
