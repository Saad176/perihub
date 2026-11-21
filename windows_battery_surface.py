"""Render the combined battery readout in the taskbar's own window layer."""

import ctypes
from ctypes import wintypes as w


user32 = ctypes.WinDLL("user32")
gdi32 = ctypes.WinDLL("gdi32")


class BitmapHeader(ctypes.Structure):
    _fields_ = [
        ("size", w.DWORD), ("width", w.LONG), ("height", w.LONG),
        ("planes", w.WORD), ("bits", w.WORD), ("unused", w.DWORD * 6),
    ]


class BlendFunction(ctypes.Structure):
    _fields_ = [("op", w.BYTE), ("flags", w.BYTE), ("alpha", w.BYTE), ("format", w.BYTE)]


def bind(dll, name, result, *arguments):
    function = getattr(dll, name)
    function.argtypes = arguments
    function.restype = result
    return function


H = w.HANDLE
point_ptr = ctypes.POINTER(w.POINT)
find_window = bind(user32, "FindWindowExW", H, H, H, w.LPCWSTR, w.LPCWSTR)
get_rect = bind(user32, "GetWindowRect", w.BOOL, H, ctypes.POINTER(w.RECT))
screen_to_client = bind(user32, "ScreenToClient", w.BOOL, H, point_ptr)
create_window = bind(user32, "CreateWindowExW", H, w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD,
                     ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, H, H, H, ctypes.c_void_p)
get_ancestor = bind(user32, "GetAncestor", H, H, w.UINT)
destroy_window = bind(user32, "DestroyWindow", w.BOOL, H)
show_window = bind(user32, "ShowWindow", w.BOOL, H, ctypes.c_int)
position_window = bind(user32, "SetWindowPos", w.BOOL, H, H, ctypes.c_int, ctypes.c_int,
                       ctypes.c_int, ctypes.c_int, w.UINT)
update_layered = bind(user32, "UpdateLayeredWindow", w.BOOL, H, H, point_ptr,
                      ctypes.POINTER(w.SIZE), H, point_ptr, w.COLORREF,
                      ctypes.POINTER(BlendFunction), w.DWORD)
create_dc = bind(gdi32, "CreateCompatibleDC", H, H)
delete_dc = bind(gdi32, "DeleteDC", w.BOOL, H)
create_dib = bind(gdi32, "CreateDIBSection", H, H, ctypes.POINTER(BitmapHeader), w.UINT,
                  ctypes.POINTER(ctypes.c_void_p), H, w.DWORD)
select_object = bind(gdi32, "SelectObject", H, H, H)
delete_object = bind(gdi32, "DeleteObject", w.BOOL, H)


def taskbar_at(left, top, width, height):
    for name in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
        taskbar = find_window(None, None, name, None)
        while taskbar:
            bounds = w.RECT()
            if (get_rect(taskbar, ctypes.byref(bounds))
                    and bounds.left <= left < left + width <= bounds.right
                    and bounds.top <= top < top + height <= bounds.bottom):
                return taskbar
            taskbar = find_window(None, taskbar, name, None)
    return None


def paint_surface(window, image):
    dc = create_dc(None)
    if not dc:
        return False
    width, height = image.width(), image.height()
    header = BitmapHeader(ctypes.sizeof(BitmapHeader), width, -height, 1, 32)
    pixels = ctypes.c_void_p()
    bitmap = create_dib(dc, ctypes.byref(header), 0, ctypes.byref(pixels), None, 0)
    if not bitmap:
        delete_dc(dc)
        return False
    previous = select_object(dc, bitmap)
    try:
        ctypes.memmove(pixels, bytes(image.constBits()), image.sizeInBytes())
        return bool(update_layered(window, None, None, ctypes.byref(w.SIZE(width, height)),
                                   dc, ctypes.byref(w.POINT()), 0,
                                   ctypes.byref(BlendFunction(0, 0, 255, 1)), 2))  # ULW_ALPHA
    finally:
        select_object(dc, previous)
        delete_object(bitmap)
        delete_dc(dc)


class BatterySurface:
    def __init__(self):
        self.window = None
        self.visible = False
        self.position = None
        self.image_key = None

    def display(self, bounds, image_key, render):
        left, top, width, height = bounds
        taskbar = taskbar_at(*bounds)
        if not taskbar:
            return False
        point = w.POINT(left, top)
        if not screen_to_client(taskbar, ctypes.byref(point)):
            return False

        if not self.window or get_ancestor(self.window, 1) != taskbar:  # GA_PARENT
            self.close()
            # WS_EX_NOACTIVATE | WS_EX_LAYERED | WS_EX_TRANSPARENT.
            # The child follows Explorer across shell flyouts, fullscreen and auto-hide.
            self.window = create_window(0x08080020, "Static", "PeriHub battery widget", 0x40000000,
                                        point.x, point.y, width, height, taskbar, None, None, None)
            if not self.window:
                return False

        if self.image_key != image_key:
            if not paint_surface(self.window, render()):
                return False
            self.image_key = image_key

        position = (point.x, point.y, width, height)
        if not self.visible or position != self.position:
            # SWP_SHOWWINDOW | SWP_NOACTIVATE, with HWND_TOP among taskbar children.
            if not position_window(self.window, None, *position, 0x50):
                return False
            self.position = position
            self.visible = True
        return True

    def hide(self):
        if self.window and self.visible:
            show_window(self.window, 0)  # SW_HIDE
            self.visible = False

    def close(self):
        if self.window:
            destroy_window(self.window)
            self.__init__()
