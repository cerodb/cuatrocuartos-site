"""Reject internal files before this repository is published by GitHub Pages."""
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
CONTROL = {'.github/check_publication.py', '.github/workflows/publication-safety.yml'}
SPECIAL = {'CNAME', '.nojekyll', '.gitignore'}
TEXT_FILES = {'llms.txt', 'robots.txt', 'media/cuatrocuartos/album/EP2/www.rockontherocks.com.txt'}
EXTENSIONS = {'.html', '.css', '.xml', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp3'}
PRIVATE_DIRS = {'reports', 'input', 'spec', 'ops', 'tests', 'backup', 'backups',
                'node_modules', '__pycache__', 'js_cache', '_large-files-excluded'}
INTERNAL = re.compile(rb'Archivo grande excluido del repositorio Git|/home/motobot/|/Users/|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')


def inspect(name, mode):
    path = PurePosixPath(name)
    if mode not in {'100644', '100755'}:
        return 'symlink or submodule is not publishable'
    if name in CONTROL:
        return None  # Public CI code: changes require explicit diff review.
    if name not in SPECIAL:
        if any(part.startswith('.') or part.lower() in PRIVATE_DIRS for part in path.parts):
            return 'private path'
        if path.suffix.lower() == '.txt':
            if name not in TEXT_FILES:
                return 'text file requires explicit review'
        elif path.suffix.lower() not in EXTENSIONS:
            return 'unapproved file type'
    if path.suffix.lower() in {'.html', '.css', '.xml', '.txt'} or name in SPECIAL:
        if INTERNAL.search((ROOT / name).read_bytes()):
            return 'internal metadata or private-key marker'
    return None


errors = []
entries = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=ROOT).decode().split('\0')
for entry in filter(None, entries):
    metadata, name = entry.split('\t', 1)
    mode, _, stage = metadata.split()
    reason = 'unmerged entry' if stage != '0' else inspect(name, mode)
    if reason:
        errors.append((name, reason))
for name, reason in errors:
    print(f'BLOCKED {name}: {reason}')
if errors:
    sys.exit(1)
print('Publication safety passed: tracked files match the reviewed public-file policy.')
