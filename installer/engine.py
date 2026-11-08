"""Standalone checksum-guarded delta installer. No Unity tooling on the target PC."""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
import bsdiff4

EXE = 'EscapeAcademy2Back2School.exe'


def digest(data): return hashlib.sha256(data).hexdigest()


def load_manifest(payload):
    return json.loads((Path(payload) / 'package.json').read_text(encoding='utf-8'))


def target_path(game, relative):
    game = Path(game).resolve(); target = (game / relative).resolve()
    target.relative_to(game)
    return target


def inspect(game, payload):
    game = Path(game)
    if not (game / EXE).is_file(): raise ValueError('В этой папке не найдена Escape Academy 2: Back 2 School.')
    states = []
    for item in load_manifest(payload)['files']:
        path = target_path(game, item['container'])
        if not path.is_file(): raise ValueError('Не найден файл игры: ' + path.name)
        current = digest(path.read_bytes())
        if current == item['source_sha256']: states.append('original')
        elif current == item['patch_sha256']: states.append('russian')
        else: raise ValueError('Версия файлов отличается от поддерживаемой сборки. Игра не изменена.')
    return 'russian' if all(s == 'russian' for s in states) else 'original' if all(s == 'original' for s in states) else 'mixed'


def ensure_closed():
    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ' + EXE, '/FO', 'CSV', '/NH'],
                            capture_output=True, creationflags=creationflags)
    if EXE.lower().encode() in result.stdout.lower(): raise ValueError('Сначала закрой игру, затем повтори установку.')


def apply(game, payload, action, progress=lambda value, text: None, check_process=True):
    if action not in ('install', 'remove'): raise ValueError('Unknown action')
    if check_process: ensure_closed()
    game, payload = Path(game).resolve(), Path(payload)
    inspect(game, payload)
    manifest = load_manifest(payload); jobs = []; staged = []
    try:
        for i, item in enumerate(manifest['files']):
            progress(i * 35, 'Проверяем файлы и готовим перевод…' if action == 'install' else 'Готовим восстановление оригинала…')
            target = target_path(game, item['container']); prior = target.read_bytes()
            current = digest(prior)
            desired = item['patch_sha256'] if action == 'install' else item['source_sha256']
            if current == desired: continue
            delta = payload / item['forward' if action == 'install' else 'reverse']
            patch = delta.read_bytes()
            if digest(patch) != item['forward_sha256' if action == 'install' else 'reverse_sha256']:
                raise ValueError('Повреждён установщик. Файлы игры не заменены.')
            result = bsdiff4.patch(prior, patch)
            if digest(result) != desired: raise ValueError('Проверка результата не пройдена. Файлы игры не заменены.')
            # Original backups are local only, never distributed in the installer.
            if current == item['source_sha256']:
                build = str(manifest.get('game_build', 'legacy'))
                if not build.isdigit() and build != 'legacy': raise ValueError('Invalid build identifier')
                backup = target_path(game / '.ea2-russian' / build / 'original', item['container'])
                backup.relative_to(game)
                backup.parent.mkdir(parents=True, exist_ok=True)
                if backup.exists() and digest(backup.read_bytes()) != current:
                    raise ValueError('Резервная копия отличается от оригинала. Замена отменена.')
                if not backup.exists(): shutil.copy2(target, backup)
            temporary = target.with_name(target.name + '.ea2-ru-stage')
            if temporary.exists(): raise ValueError('Остался временный файл предыдущей операции. Нужна проверка: ' + str(temporary))
            with temporary.open('xb') as stream:
                stream.write(result); stream.flush(); os.fsync(stream.fileno())
            staged.append(temporary)
            jobs.append((target, temporary, prior, desired))
        if check_process: ensure_closed()
        changed = []
        try:
            for target, temporary, prior, desired in jobs:
                if digest(target.read_bytes()) != digest(prior): raise ValueError('Файл игры изменился во время подготовки.')
                os.replace(temporary, target); changed.append((target, prior))
                if digest(target.read_bytes()) != desired: raise ValueError('Ошибка проверки установленного файла.')
        except Exception:
            for target, prior in reversed(changed):
                recovery = target.with_name(target.name + '.ea2-ru-rollback')
                recovery.write_bytes(prior); os.replace(recovery, target)
            raise
        progress(100, 'Русификатор установлен. Выбери English в игре.' if action == 'install' else 'Оригинальные файлы восстановлены.')
    finally:
        for temporary in staged:
            if temporary.exists(): temporary.unlink()
    return inspect(game, payload)
