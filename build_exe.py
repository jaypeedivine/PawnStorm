import subprocess, sys
subprocess.run([
    sys.executable, '-m', 'PyInstaller',
    '--onefile', '--windowed',
    '--icon=pawnstorm.ico',
    '--name=PawnStorm',
    '--add-data', 'fonts;fonts',
    'main.py'
], check=True)
