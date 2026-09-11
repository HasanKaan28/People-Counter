"""
Automated Build & GitHub Release Pipeline for AI Camera People Counter.
Usage:
    python build_release.py [version] [release_notes_optional]
Example:
    python build_release.py 1.2.0 "Added new multi-camera support"
"""

import sys
import os
import subprocess
import zipfile
import json
import urllib.request
import ctypes
from ctypes import wintypes

CSC_PATH = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
REPO = "HasanKaan28/kamera-kisi-sayaci"

def get_github_token():
    advapi32 = ctypes.windll.advapi32
    class CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ('Flags', wintypes.DWORD),
            ('Type', wintypes.DWORD),
            ('TargetName', wintypes.LPWSTR),
            ('Comment', wintypes.LPWSTR),
            ('LastWritten', wintypes.FILETIME),
            ('CredentialBlobSize', wintypes.DWORD),
            ('CredentialBlob', ctypes.POINTER(ctypes.c_byte)),
            ('Persist', wintypes.DWORD),
            ('AttributeCount', wintypes.DWORD),
            ('Attributes', ctypes.c_void_p),
            ('TargetAlias', wintypes.LPWSTR),
            ('UserName', wintypes.LPWSTR),
        ]

    PCREDENTIAL = ctypes.POINTER(CREDENTIAL)
    CredRead = advapi32.CredReadW
    CredRead.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(PCREDENTIAL)]
    CredRead.restype = wintypes.BOOL

    pcred = PCREDENTIAL()
    if CredRead('git:https://github.com', 1, 0, ctypes.byref(pcred)):
        raw = ctypes.string_at(pcred.contents.CredentialBlob, pcred.contents.CredentialBlobSize)
        token = raw.decode('utf-16le', errors='ignore')
        if not token.startswith('gh'):
            token = raw.decode('utf-8', errors='ignore')
        return token.strip()
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

def build_executables():
    print("=== [1/5] Compiling PeopleCounter.exe ===")
    cmd_pc = [
        CSC_PATH, "/nologo", "/target:winexe",
        "/r:System.Windows.Forms.dll", "/r:System.Drawing.dll",
        "/win32icon:app.ico",
        "/out:PeopleCounter.exe", "PeopleCounter.cs"
    ]
    subprocess.check_call(cmd_pc)
    print("[OK] PeopleCounter.exe compiled.")

    print("=== [2/5] Creating embedded payload.zip ===")
    files_to_pack = [
        'PeopleCounter.exe', 'PeopleCounter.cs', 'Setup.bat', 'Start.bat', 'Install.bat',
        'install.sh', 'start.sh', 'app.py', 'config.py', 'config.json', 'database.py',
        'tracker.py', 'camera_stream.py', 'google_sync.py', 'google_apps_script_template.js',
        'requirements.txt', 'README.md', 'USER_GUIDE.md', 'yolov8n.pt', 'app.ico',
        os.path.join('templates', 'index.html')
    ]
    with zipfile.ZipFile("payload.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files_to_pack:
            if os.path.exists(f):
                zf.write(f, arcname=f)
    print(f"[OK] payload.zip created ({os.path.getsize('payload.zip')} bytes).")

    print("=== [3/5] Compiling PeopleCounter-Setup.exe ===")
    cmd_setup = [
        CSC_PATH, "/nologo", "/target:winexe",
        "/resource:payload.zip,payload.zip",
        "/win32icon:app.ico",
        "/out:PeopleCounter-Setup.exe",
        "/r:System.Windows.Forms.dll", "/r:System.Drawing.dll",
        "/r:System.IO.Compression.FileSystem.dll", "/r:System.IO.Compression.dll",
        "PeopleCounterSetup.cs"
    ]
    subprocess.check_call(cmd_setup)
    print(f"[OK] PeopleCounter-Setup.exe compiled ({os.path.getsize('PeopleCounter-Setup.exe')} bytes).")
    if os.path.exists("payload.zip"):
        os.remove("payload.zip")

def sync_git_and_release(version_tag, notes=""):
    token = get_github_token()
    if not token:
        print("[ERROR] GitHub token not found.")
        return

    tag_name = f"v{version_tag.lstrip('v')}"
    print(f"=== [4/5] Git commit and push for {tag_name} ===")
    
    subprocess.run(["git", "add", "-A"])
    commit_msg = f"release: Bump version to {tag_name}"
    subprocess.run(["git", "commit", "-m", commit_msg])
    subprocess.run(["git", "push", "origin", "main"])
    subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"])
    subprocess.run(["git", "push", "origin", tag_name])

    print(f"=== [5/5] Creating GitHub Release {tag_name} & Uploading Assets ===")
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'PeopleCounter-BuildPipeline'
    }

    release_body = notes if notes else f"## Release {tag_name}\n\n- Standalone PeopleCounter-Setup.exe installer\n- Upgraded performance and bugfixes."
    payload = {
        'tag_name': tag_name,
        'name': f"{tag_name} - AI Camera People Counter & Revenue Tracker",
        'body': release_body,
        'draft': False,
        'prerelease': False
    }

    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases",
        data=json.dumps(payload).encode('utf-8'),
        headers={**headers, 'Content-Type': 'application/json'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as resp:
            rel_data = json.loads(resp.read().decode())
            upload_url = rel_data.get('upload_url').split('{')[0]
    except urllib.error.HTTPError as e:
        if e.code == 422:
            req_get = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases/tags/{tag_name}", headers=headers)
            with urllib.request.urlopen(req_get) as resp_get:
                rel_data = json.loads(resp_get.read().decode())
                upload_url = rel_data.get('upload_url').split('{')[0]
        else:
            raise

    # Package Zip Release
    zip_filename = f"PeopleCounter-{tag_name}-Windows.zip"
    print(f"Creating release package: {zip_filename}...")
    release_files = [
        'PeopleCounter-Setup.exe', 'PeopleCounter.exe', 'Setup.bat', 'Start.bat', 'Install.bat',
        'install.sh', 'start.sh', 'app.py', 'config.py', 'config.json', 'database.py',
        'tracker.py', 'camera_stream.py', 'google_sync.py', 'google_apps_script_template.js',
        'requirements.txt', 'README.md', 'USER_GUIDE.md', 'yolov8n.pt', 'app.ico',
        os.path.join('templates', 'index.html')
    ]
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rf in release_files:
            if os.path.exists(rf):
                zf.write(rf, arcname=rf)

    # Upload Assets
    assets = [
        ('PeopleCounter-Setup.exe', 'application/vnd.microsoft.portable-executable'),
        ('PeopleCounter.exe', 'application/vnd.microsoft.portable-executable'),
        (zip_filename, 'application/zip')
    ]

    for filename, content_type in assets:
        if not os.path.exists(filename): continue
        with open(filename, 'rb') as f:
            data = f.read()
        up_req = urllib.request.Request(
            f"{upload_url}?name={filename}",
            data=data,
            headers={
                **headers,
                'Content-Type': content_type,
                'Content-Length': str(len(data))
            },
            method='POST'
        )
        try:
            with urllib.request.urlopen(up_req) as up_resp:
                print(f"[OK] Uploaded {filename} to GitHub Release {tag_name} (Status: {up_resp.status})")
        except urllib.error.HTTPError as ue:
            print(f"[WARN] Upload {filename} status: {ue.code}")

    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    print(f"\n✨ Successfully built and published {tag_name} to GitHub!")

def install_locally():
    print("=== [6/6] Installing latest version locally to AppData\\Local\\Programs\\PeopleCounter ===")
    local_app_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "PeopleCounter")
    if not os.path.exists(local_app_dir):
        os.makedirs(local_app_dir, exist_ok=True)

    files_to_copy = [
        'PeopleCounter.exe', 'PeopleCounter-Setup.exe', 'Setup.bat', 'Start.bat', 'Install.bat',
        'install.sh', 'start.sh', 'app.py', 'config.py', 'config.json', 'database.py',
        'tracker.py', 'camera_stream.py', 'google_sync.py', 'google_apps_script_template.js',
        'requirements.txt', 'README.md', 'USER_GUIDE.md', 'yolov8n.pt', 'app.ico'
    ]
    import shutil
    for f in files_to_copy:
        if os.path.exists(f):
            dest = os.path.join(local_app_dir, f)
            shutil.copy2(f, dest)

    tmpl_src = os.path.join('templates', 'index.html')
    tmpl_dst_dir = os.path.join(local_app_dir, 'templates')
    if os.path.exists(tmpl_src):
        os.makedirs(tmpl_dst_dir, exist_ok=True)
        shutil.copy2(tmpl_src, os.path.join(tmpl_dst_dir, 'index.html'))

    # Update shortcuts
    ps_cmd = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$target = '{os.path.join(local_app_dir, 'PeopleCounter.exe')}'; "
        f"$ico = '{os.path.join(local_app_dir, 'app.ico')}'; "
        "$d1 = [Environment]::GetFolderPath('Desktop'); "
        "$d2 = (Join-Path $env:USERPROFILE 'OneDrive\\Desktop'); "
        "$d3 = (Join-Path $env:USERPROFILE 'OneDrive\\Masaüstü'); "
        "$d4 = (Join-Path $env:USERPROFILE 'Desktop'); "
        "foreach($dir in @($d1,$d2,$d3,$d4)) { "
        "  if (Test-Path $dir) { "
        "    try { "
        "      $s = $ws.CreateShortcut((Join-Path $dir 'People Counter.lnk')); "
        "      $s.TargetPath = $target; "
        f"      $s.WorkingDirectory = '{local_app_dir}'; "
        "      $s.Description = 'AI Camera People Counter & Revenue Tracker'; "
        "      $s.IconLocation = $ico; "
        "      $s.Save() "
        "    } catch {} "
        "  } "
        "}"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    print(f"[OK] Local installation updated successfully at: {local_app_dir}")

if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "1.1.0"
    notes = sys.argv[2] if len(sys.argv) > 2 else ""
    build_executables()
    sync_git_and_release(version, notes)
    install_locally()
