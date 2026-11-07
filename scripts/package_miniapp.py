"""Build a source import bundle containing only the native miniapp."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
source = root / 'frontend' / 'miniapp'
output = root / 'dist' / 'ktv-miniapp-v0.3.0.zip'
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(source.rglob('*')):
        if file.is_file() and file.suffix in {'.js', '.json', '.wxml', '.wxss', '.md'}:
            if file.name == 'project.private.config.json':
                continue
            archive.write(file, file.relative_to(source).as_posix())
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert 'app.json' in archive.namelist()
print(output)

# A separate complete source bundle avoids confusing the miniapp-only ZIP with
# the whole application. It contains no bill images, DBs, dependencies or secrets.
complete = root / 'dist' / 'ktv-fullstack-v0.3.0.zip'
excluded = {'node_modules', '__pycache__', 'dist', '.pytest_cache'}
extensions = {'.py', '.txt', '.md', '.json', '.vue', '.ts', '.js', '.cjs', '.wxml', '.wxss', '.css', '.html', '.yml', '.yaml', '.bat'}
with zipfile.ZipFile(complete, 'w', zipfile.ZIP_DEFLATED) as archive:
    for directory in ('backend', 'frontend', 'docs', 'scripts', '.github'):
        for file in sorted((root/directory).rglob('*')):
            relative = file.relative_to(root)
            if (file.is_file() and not excluded.intersection(relative.parts)
                    and file.name != 'project.private.config.json'
                    and (file.suffix in extensions or file.name == 'Dockerfile')):
                archive.write(file, relative.as_posix())
    for name in ('README.md', 'AGENTS.md', '.gitignore', '.dockerignore', '.env.example', 'compose.yaml'):
        archive.write(root/name, name)
with zipfile.ZipFile(complete) as archive:
    assert archive.testzip() is None
    assert 'backend/app/main.py' in archive.namelist()
print(complete)
