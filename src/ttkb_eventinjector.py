"""
Injects custom global events into patched ttkbootstrap methods to support better UI reactivity.

This module wraps internal `ttkbootstrap` functions such as `theme_use`, `theme_create`, and `mainloop`
to automatically emit custom Tkinter events at specific stages (e.g., before and after theme changes or app startup).
This enables global event-based hooking for styling and initialization logic.

To receive these events, use `.bind_all("<EventName>", callback, add=True)`:
Example:
    root.bind_all("<<PreMainloop>>", on_pre_mainloop, add=True)
    root.bind_all("<<PostThemeUse>>", on_post_theme_use, add=True)

WARNING:
Always use `add=True` when binding to ensure existing event listeners are preserved.

Author: sora_7672
"""


__author__ = "sora_7672"

import ttkbootstrap as tb

if not globals().get("__PATCHED", False):
    __PATCHED = False
    __ORIGINAL = {}
    __ROOT = None


def __handle_key_error(error):
    """
    Raises a descriptive runtime error when a patched original function is missing.

    Used internally to signal misconfiguration or incorrect patching.

    :param error: KeyError (The error raised due to missing function in `__ORIGINAL`)
    :raises RuntimeError: With message and original error content.
    """

    raise RuntimeError("The original function is not linked properly in '_ORIGINAL' in the ttkb_eventinjector.py\n",
                       str(error))


def __theme_use(*args, **kwargs):
    """
    Wrapped version of ttkbootstrap `theme_use` to emit global events before and after the call.

    Generates:
        <<PreThemeUse>> before calling the original method
        <<PostThemeUse>> after the method returns

    :return: Any (The result of the original `theme_use` call)
    """

    global __ORIGINAL, __ROOT
    __ROOT.event_generate("<<PreThemeUse>>", when="tail")
    try:
        out = __ORIGINAL["root.style.theme_use"](*args, **kwargs)
    except KeyError as e:
        __handle_key_error(e)
    __ROOT.event_generate("<<PostThemeUse>>", when="tail")
    return out


def __theme_create(*args, **kwargs):
    """
    Wrapped version of ttkbootstrap `theme_create` to emit events around theme creation.

    Generates:
        <<PreThemeCreation>> before calling the original method
        <<PostThemeCreation>> after the method returns

    :return: Any (The result of the original `theme_create` call)
    """

    global __ORIGINAL, __ROOT
    __ROOT.event_generate("<<PreThemeCreation>>", when="tail")
    try:
        out = __ORIGINAL["root.style.theme_create"](*args, **kwargs)
    except KeyError as e:
        __handle_key_error(e)
    __ROOT.event_generate("<<PostThemeCreation>>", when="tail")
    return out


def __mainloop(*args, **kwargs):
    """
    Wrapped version of ttkbootstrap `mainloop` to emit a global event before entering the loop.

    Generates:
        <<PreMainloop>> before entering the main event loop.

    :return: Any (The result of the original `mainloop` call)
    """

    global __ORIGINAL, __ROOT
    __ROOT.event_generate("<<PreMainloop>>", when="tail")
    try:
        out = __ORIGINAL["mainloop"](*args, **kwargs)
    except KeyError as e:
        __handle_key_error(e)
    return out


def __after_root():
    """
    Performs late-stage patching of theme-related methods and mainloop on the root window.

    Called internally after a ttkbootstrap `Window` is created.
    Overwrites `theme_use`, `theme_create`, and `mainloop` with event-emitting versions.

    :return: None
    """

    global __ROOT, __ORIGINAL
    __ORIGINAL["root.style.theme_use"] = __ROOT.style.theme_use
    __ROOT.style.theme_use = __theme_use

    __ORIGINAL["root.style.theme_create"] = __ROOT.style.theme_create
    __ROOT.style.theme_create = __theme_create

    __ORIGINAL["mainloop"] = __ORIGINAL["Window"].mainloop
    __ORIGINAL["Window"].mainloop = __mainloop


def __window(*args, **kwargs):
    """
    Patched replacement for `ttkbootstrap.Window`.

    Creates the root window, stores it internally, performs post-initialization patching,
    and emits a global event `<<PostRootInit>>` to signal full root setup.

    :return: Window (The created ttkbootstrap `Window` instance)
    """

    global __ORIGINAL, __ROOT
    try:
        out = __ORIGINAL["Window"](*args, **kwargs)
        __ROOT = out
    except KeyError as e:
        __handle_key_error(e)
    __after_root()
    __ROOT.event_generate("<<PostRootInit>>", when="tail")
    return out


def __patch():
    """
    Applies one-time patching to ttkbootstrap's `Window` constructor.

    Ensures that the first instantiation of `Window` uses the wrapped version that supports event injection.

    :return: None
    """

    global __PATCHED, __ORIGINAL
    if __PATCHED:
        return

    __ORIGINAL["Window"] = tb.Window

    tb.Window = __window
    __PATCHED = True

# used to call once on import the internal function
__patch()


