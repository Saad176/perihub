"""Temporary developer helper to list AULA child controls."""

import ctypes
import sys
from ctypes import wintypes

u = ctypes.windll.user32
root = int(sys.argv[1])
root_rect = wintypes.RECT()
u.GetWindowRect(root, ctypes.byref(root_rect))


@ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def visit(hwnd, _):
    cls = ctypes.create_unicode_buffer(128)
    title = ctypes.create_unicode_buffer(256)
    rect = wintypes.RECT()
    u.GetClassNameW(hwnd, cls, 128)
    u.GetWindowTextW(hwnd, title, 256)
    u.GetWindowRect(hwnd, ctypes.byref(rect))
    x, y = rect.left - root_rect.left, rect.top - root_rect.top
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w > 0 and h > 0:
        print(hwnd, cls.value, repr(title.value), (x, y, w, h), "visible", bool(u.IsWindowVisible(hwnd)))
    return True


u.EnumChildWindows(root, visit, 0)
