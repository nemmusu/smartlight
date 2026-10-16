"""Export the shared Windows/Linux sources without local state or build environments."""
from pathlib import Path
import zipfile
from export_repository import RUNTIME

PROJECT=Path(__file__).resolve().parents[1]


def export():
    version=(PROJECT/'version.txt').read_text(encoding='utf-8').strip()
    output=PROJECT/'dist'/f'Smartlight-{version}-source.zip'
    output.parent.mkdir(exist_ok=True)
    files=[PROJECT/name for name in RUNTIME if (PROJECT/name).is_file()]
    files.extend(p for p in PROJECT.glob('test_*') if p.is_file() and p.suffix in {'.py','.cjs'})
    for folder in ['ui','legacy_hwlight','installer','docs','.github']:
        files.extend(p for p in (PROJECT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc','.pyo'} and not (folder=='installer' and p.suffix=='.png'))
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in sorted(files):
            archive.write(path,arcname=f'Smartlight-{version}/'+path.relative_to(PROJECT).as_posix())
    print(output)
    return output


if __name__=='__main__':
    export()
