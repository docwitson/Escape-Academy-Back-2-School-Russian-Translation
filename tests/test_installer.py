import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import bsdiff4
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'installer'))
import engine


class Installer(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.game = Path(self.temp.name) / 'game'; self.game.mkdir()
        self.payload = Path(self.temp.name) / 'payload'; self.payload.mkdir()
        (self.game / engine.EXE).touch(); self.items = []
        for i in range(2):
            original, russian = b'original' + bytes([i]), 'Перевод'.encode() + bytes([i])
            (self.game / f'{i}.assets').write_bytes(original)
            item = dict(container=f'{i}.assets', source_sha256=engine.digest(original), patch_sha256=engine.digest(russian))
            for direction, a, b in [('forward', original, russian), ('reverse', russian, original)]:
                delta = bsdiff4.diff(a, b); name = f'{i}-{direction}.bsdiff'; (self.payload / name).write_bytes(delta)
                item[direction] = name; item[direction + '_sha256'] = engine.digest(delta)
            self.items.append(item)
        (self.payload / 'package.json').write_text(json.dumps(dict(files=self.items)))

    def run_action(self, action): return engine.apply(self.game, self.payload, action, check_process=False)

    def test_roundtrip_and_repeat_install(self):
        self.assertEqual(self.run_action('install'), 'russian')
        self.assertEqual(self.run_action('install'), 'russian')
        self.assertEqual(self.run_action('remove'), 'original')
        self.assertEqual(self.run_action('remove'), 'original')

    def test_remove_previous_patch_without_backup(self):
        for item in self.items:
            file = self.game / item['container']
            file.write_bytes(bsdiff4.patch(file.read_bytes(), (self.payload / item['forward']).read_bytes()))
        self.assertFalse((self.game / '.ea2-russian').exists())
        self.assertEqual(self.run_action('remove'), 'original')

    def test_wrong_game_version_never_changes_other_file(self):
        (self.game / '1.assets').write_bytes(b'updated game')
        before = (self.game / '0.assets').read_bytes()
        with self.assertRaises(ValueError): self.run_action('install')
        self.assertEqual((self.game / '0.assets').read_bytes(), before)

    def test_corrupt_second_delta_leaves_both_original(self):
        (self.payload / self.items[1]['forward']).write_bytes(b'corrupt')
        with self.assertRaises(ValueError): self.run_action('install')
        self.assertEqual(engine.inspect(self.game, self.payload), 'original')
        self.assertFalse(list(self.game.glob('*.ea2-ru-stage')))

    def test_failure_replacing_second_file_rolls_back_first(self):
        real = engine.os.replace; calls = []
        def fail_second(a, b):
            calls.append(str(a))
            if len(calls) == 2: raise OSError('simulated failure')
            return real(a, b)
        with patch.object(engine.os, 'replace', side_effect=fail_second):
            with self.assertRaises(OSError): self.run_action('install')
        self.assertEqual(engine.inspect(self.game, self.payload), 'original')

    def test_interrupted_mixed_install_can_resume(self):
        item = self.items[0]; file = self.game / item['container']
        file.write_bytes(bsdiff4.patch(file.read_bytes(), (self.payload / item['forward']).read_bytes()))
        self.assertEqual(engine.inspect(self.game, self.payload), 'mixed')
        self.assertEqual(self.run_action('install'), 'russian')

    def test_paths_cannot_escape_game_directory(self):
        with self.assertRaises(ValueError): engine.target_path(self.game, '../outside')

    def test_old_build_backup_does_not_block_new_build(self):
        manifest = dict(game_build='26497480', files=self.items)
        (self.payload / 'package.json').write_text(json.dumps(manifest))
        legacy = self.game / '.ea2-russian/original/0.assets'
        legacy.parent.mkdir(parents=True); legacy.write_bytes(b'previous build')
        self.assertEqual(self.run_action('install'), 'russian')
        backup = self.game / '.ea2-russian/26497480/original/0.assets'
        self.assertEqual(engine.digest(backup.read_bytes()), self.items[0]['source_sha256'])
        self.assertEqual(legacy.read_bytes(), b'previous build')
