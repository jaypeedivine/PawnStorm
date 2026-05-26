[app]
title = PawnStorm
package.name = pawnstorm
package.domain = org.pawnstorm
source.dir = .
source.include_exts = py,png,ttf,ico
source.exclude_dirs = __pycache__,.buildozer,bin
version = 1.0.0
requirements = python3,pygame,chess
icon.filename = pawnstorm_icon.png
orientation = portrait,landscape
fullscreen = 0
android.permissions =
android.api = 33
android.minapi = 21
android.ndk = 25b
android.accept_sdk_license = True
android.arch = arm64-v8a
p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1
