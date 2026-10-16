"""Export an allowlisted public repository, excluding all local state and probes."""
from pathlib import Path
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
RUNTIME = {
    '__init__.py','app.py','bridge_client.py','mcp_manager.py','mcp_server.py','mystic_light.py',
    'pc.py','pc_scenes.py','pc_discovery.py','service.py','startup.py','storage.py','tapo.py','tapo_bulb_native.py',
    'tray.py','windows_clipboard.py','version.txt','requirements.txt','requirements-mcp.txt',
    '.gitignore','README.md','README.it.md','FIRST_RUN.md','LINUX.md','CONTRIBUTING.md','SECURITY.md','CHANGELOG.md','package.json',
}

def export():
    version = (PROJECT/'version.txt').read_text().strip()
    output = PROJECT/'dist'/f'Smartlight-{version}-repository.zip'
    files = [PROJECT/name for name in RUNTIME if (PROJECT/name).is_file()]
    files += [p for p in PROJECT.glob('test_*') if p.is_file() and p.suffix in {'.py','.cjs'}]
    for folder in ['ui','legacy_hwlight','installer','docs','.github']:
        if not (PROJECT/folder).exists(): continue
        files += [p for p in (PROJECT/folder).rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'}
                  and not (folder=='installer' and p.suffix=='.png')]
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path,'Smartlight/'+path.relative_to(PROJECT).as_posix())
    print(output)
    return output

if __name__ == '__main__': export()
