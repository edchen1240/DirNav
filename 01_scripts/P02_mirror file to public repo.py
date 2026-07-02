#!/usr/bin/env python3
"""
[P02_mirror file to public repo.py]
Purpose:
    Mirro files to repo directory, so my update is both alive on my local machine and on the public repo.
Author: Meng-Chi Ed Chen
Date:
Reference:
    1. Replaces the prior generate.ts + types.ts.
    2. Pure stdlib, no external dependencies.

Status: Working.
"""
import os, sys, re, json, shutil, time, subprocess
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
HTML_DIR = ROOT / "02_html"
INCLUDES_DIR = HTML_DIR / "04_includes"
JSON_PATH = ROOT / "projects.json"
OUT_PATH = HTML_DIR / "index.html"

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})?$")
SLUG_RE = re.compile(r"^\S+$")

PROJECT_FIELDS = (
    "projectSlug", "projectName", "attributes", "priority", "status",
    "p00InitiationDate", "startDate", "lastWorkDate", "note",
    "folders", "urls", "files", "related", "p00",
)
STATUS_FIELDS = ("value", "label", "description", "dim", "order")




def replacement_single_file(path_A: Path, path_B: Path, verbose=False):
    """
    Replace the content of file B with the content of file A.
    """
    #[1] Read the content of file A and write it to file B.
    print(f'\n[replacement_single_file] {path_A} -> {path_B}') if verbose else None
    with open(path_A, "r", encoding="utf-8") as f:
        content_A = f.read()
    with open(path_B, "w", encoding="utf-8") as f:
        f.write(content_A)
    
    #[2] Read back the content of file B and compare it with content_A.
    with open(path_B, "r", encoding="utf-8") as f:
        content_B = f.read()
    if content_A != content_B:
        raise ValueError(f'❌[Error] The content of {path_B} does not match {path_A} after replacement.')
    else:
        print(f'✅[Success] Replaced {path_B} with {path_A}')




def replacement_full_dir_overwrite(path_A: Path, path_B: Path, list_filename_exclude=None, ask=True):
    """
    1. Delete all files in path_B. (If path_B does not exist, create it.)
    2. Copy all files from path_A to path_B, skipping any basename in list_filename_exclude.
    """
    list_filename_exclude = list_filename_exclude or []
    print(f'\n[replacement_full_dir_overwrite]')
    #[1] Check if path_A is a directory.
    if not path_A.is_dir():
        raise ValueError(f'❌[Error] {path_A} is not a directory.')
    #[2] Check if path_B is a directory. If not, create it.
    if not path_B.is_dir():
        print(f'-- {path_B} does not exist. Creating it.')
        path_B.mkdir(parents=True, exist_ok=True)
    #[3] Ask the user if they want to delete all files in path_B.
    if ask:
        answer = input(f'-- Do you replace everthing in {path_B} with the content of {path_A}? (Please reply "yes")\n')
        if answer.lower() != 'yes':
            print(f'-- Skipping [replacement_full_dir_overwrite].')
            return
    
    #[4] Delete all contents of path_B, then copy the full tree from path_A.
    for item in path_B.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    for item in path_A.iterdir():
        if item.name in list_filename_exclude:
            print(f'-- Skipping {item.name} (excluded from mirror).')
            continue
        dest = path_B / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    print(f'✅[Success] Replaced {path_B} with content from {path_A}')


def replacement_directory_with_matching(dir_A, dir_B, list_kwd_exclude=[], ask=True):
    """
    Update files from directory A to directory B
    After excluding files that contain any of the keywords in list_kwd_exclude, list_bsn_A and list_bsn_B should be identical.
    Then the copy will begin.
    If ask is True, the user will be prompted to confirm the copy.
    Only when 
    """
    print(f'\n[replacement_directory_with_matching]')
    #[1] Get list_bsn_A, filter out list_kwd_exclude, and putup list_path_A.
    list_bsn_A = [f.name for f in Path(dir_A).iterdir() if f.is_file()]
    list_bsn_A = [bsn for bsn in list_bsn_A if not any(kwd in bsn for kwd in list_kwd_exclude)]
    list_path_A = [Path(dir_A) / bsn for bsn in list_bsn_A]
    print(f'-- list_bsn_A: {list_bsn_A}')
    
    #[2] Get list_bsn_B, filter out list_kwd_exclude, and putup list_path_B.
    list_bsn_B = [f.name for f in Path(dir_B).iterdir() if f.is_file()]
    list_bsn_B = [bsn for bsn in list_bsn_B if not any(kwd in bsn for kwd in list_kwd_exclude)]
    list_path_B = [Path(dir_B) / bsn for bsn in list_bsn_B]
    print(f'-- list_bsn_B: {list_bsn_B}')
    
    #[3] Compare list_bsn_A and list_bsn_B, if not identical, raise an error.
    if set(list_bsn_A) != set(list_bsn_B):
        text_error =    f'\n❌[Error] The files in {dir_A} and {dir_B} are not identical after excluding keywords:\n{list_kwd_exclude}\n'
        raise ValueError(text_error)
    else:
        print(f'-- Both directories have identical files.')
        
    #[4] Replace the content of file B with the content of file A (paired by name).
    if ask:
        answer = input(f'-- Do you want to replace these files? (Please reply "yes")\n')
        if answer.lower() != 'yes':
            print(f'-- Skipping [replacement_directory_with_matching].')
            return
    for bsn in list_bsn_A:
        path_A = Path(dir_A) / bsn
        path_B = Path(dir_B) / bsn
        replacement_single_file(path_A, path_B)
        
    

def compile_public_dashboard():
    """Regenerate 12_GitHub_DirNav/02_html/index.html from its demo projects.json."""
    pub_root = ROOT / "12_GitHub_DirNav"
    script = pub_root / "01_scripts" / "P01_generate DirNav page.py"
    if not script.exists():
        raise FileNotFoundError(f"❌[Error] Public compile script not found: {script}")
    print(f"\n[compile_public_dashboard] Regenerating {pub_root / '02_html' / 'index.html'} from demo projects.json")
    subprocess.run([sys.executable, str(script)], cwd=str(script.parent), check=True)
    print("✅[Success] Public index.html regenerated from 12_GitHub_DirNav/projects.json")


if __name__ == "__main__":
    
    print(f'\n[{os.path.basename(__file__)}] Start mirroring files to public repo.')
    
    
    
    #[1] Full directory overwrite for 01_scripts (flat today; avoids filename-set mismatch).
    dir_A = ROOT / "01_scripts"
    dir_B = ROOT / "12_GitHub_DirNav" / "01_scripts"
    replacement_full_dir_overwrite(dir_A, dir_B, ask=True)

    #[2] Full directory overwrite for 02_html (skip index.html — rebuilt from demo manifest).
    dir_A = ROOT / "02_html"
    dir_B = ROOT / "12_GitHub_DirNav" / "02_html"
    replacement_full_dir_overwrite(dir_A, dir_B, list_filename_exclude=["index.html"], ask=True)

    #[3] Regenerate public index.html so GitHub Pages never serves working-tree project data.
    compile_public_dashboard()
    
    #[4] Single file replacement for root bats.
    list_bsns = ['[B]_0-Install Protocol.bat', '[B]_P01-Compile Dashboard.bat']
    
    for i_bsn in list_bsns:
        path_A = ROOT / i_bsn
        path_B = ROOT / '12_GitHub_DirNav' / i_bsn
        replacement_single_file(path_A, path_B, verbose=True)
    

    print(f'\nCompleted {os.path.basename(__file__)}. Close in 3 seconds.')
    time.sleep(3)
    