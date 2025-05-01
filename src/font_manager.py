"""
Provides font management and injection for ttkbootstrap applications.

This module wraps and patches font-related functionality from `tkinter` and `ttkbootstrap`,
ensuring consistent and centralized font handling throughout the application.

It replaces key constructors such as `Font`, `Style`, and `Window` with versions that allow
deferred initialization, extended validation, and global event binding after the main window is created.

Font definitions are tracked and stored for reuse or lookup by name.
The `FontManager` and `ProxyFont` classes provide structured access to these fonts.

Author:
    sora_7672
"""

__author__ = 'sora_7672'

from tkinter import font as tkfont
from tkinter.font import Font as TkFontClass

import ttkbootstrap as tb


if not globals().get("__PATCHED", False):
    __PATCHED = False
    __FONT_MANAGER_INITIALISED = False
    __ORIGINAL = {}
    __STYLE_OBJECT = None


def __handle_key_error(error):
    """
    Raises a descriptive runtime error when a patched original function is missing.

    Used internally to signal misconfiguration or incorrect patching.

    :param error: KeyError (The error raised due to missing function in `__ORIGINAL`)
    :raises RuntimeError: With message and original error content.
    """

    raise RuntimeError("The original function is not linked properly in '_ORIGINAL' in the ttkb_eventinjector.py\n",
                       str(error))

def __after_root() -> None:
    """
    Initializes the FontManager after the ttkbootstrap root window has been created.

    This sets up the internal font dictionary state and ensures that future font interactions
    go through the patched logic.

    :return: None
    """

    global __FONT_MANAGER_INITIALISED

    FontManager()
    __FONT_MANAGER_INITIALISED = True


def __window(*args, **kwargs) -> tb.Window:
    """
    Patched wrapper for `ttkbootstrap.Window` constructor.

    Creates the window, stores a reference, then triggers post-creation hook.

    :return: ttkbootstrap.Window instance
    :raises RuntimeError: If patch reference is broken or not defined.
    """

    global __ORIGINAL, __ROOT_OBJECT
    try:
        out = __ORIGINAL["Window"](*args, **kwargs)
        __ROOT_OBJECT = out
    except KeyError as e:
        __handle_key_error(e)
    __after_root()
    return out

def __style(*args, **kwargs) -> tb.Style:
    """
    Patched wrapper for `ttkbootstrap.Style`.

    Provides singleton-style access to the first Style object and wraps `configure` when not already patched.

    :return: ttkbootstrap.Style
    :raises RuntimeError: If patch reference is broken or not defined.
    """

    global __ORIGINAL, __STYLE_OBJECT
    if __STYLE_OBJECT is None:
        try:
            out = __ORIGINAL["Style"](*args, **kwargs)

        except KeyError as error:
            raise RuntimeError("The original function is not linked properly in '_ORIGINAL' in the ttkb_eventinjector.py\n",
                               str(error))
        __STYLE_OBJECT = out
        if "Style.configure" not in __ORIGINAL:
            __wrap_style_configure()
        return out
    else:
        return __STYLE_OBJECT

def __wrap_style_configure() -> None:
    """
    Replaces the original `Style.configure` method with a custom wrapper that adds font validation.

    This patch ensures that any future calls to `.configure()` on ttkbootstrap's Style instance
    will go through a validation layer to check that the `font` parameter is correctly set up.

    Additionally, it dynamically replaces the docstring of the patched method with an extended version
    that includes this font-related warning as well as the original documentation.

    Use this only once after initializing the root and style object.
    :return: None
    """

    global __ORIGINAL, __STYLE_OBJECT

    __ORIGINAL["Style.configure"] = __STYLE_OBJECT.configure
    __configure.__doc__ = ("Updated docstring by font_manager:\n" + str(__configure.__doc__ or "") +
                           "\n\nOriginal docstring:\n" + (__ORIGINAL["Style.configure"].__doc__ or ""))
    __STYLE_OBJECT.configure = __configure


def __configure(*args, **kwargs):
    """
    Custom wrapper for `Style.configure` that enforces strict font type checking.

    If a `font` keyword argument is passed, it ensures it's a valid `tkinter.Font` instance.
    This prevents style bugs that can occur if raw strings or incompatible font formats are used.

    Also ensures that the internal original `Style.configure` method is properly linked before calling it.

    :param args: Any positional arguments passed through to the original Style.configure.
    :param kwargs: Keyword arguments; must include a proper `Font` object if `font` is used.
    :raises TypeError: If `font` is not an instance of `tkinter.font.Font`.
    :raises RuntimeError: If the internal pointer to the original Style.configure is not available.
    :return: The result of calling the original Style.configure method.
    """

    global __ORIGINAL
    if kwargs and "font" in kwargs:
        if isinstance(kwargs["font"], tuple):
            raise TypeError("The font argument cant be a tuple instance to ensure correct initialization!\n"
                            "Use either the standard tk.Font object or a proxy for it.")
    try:

        out = __ORIGINAL["Style.configure"](*args, **kwargs)
    except KeyError as error:
        raise RuntimeError("The original function is not linked properly in '_ORIGINAL' in the font_manager.py\n",
                           str(error))
    return out

# Todo: maybe i forget to ensure fonts allways have names (if not we should use a random hash or so)
def __font(*args, **kwargs) -> None:
    """
    Patches the `tkinter.font.Font` constructor.

    Tracks font definitions internally via FontManager, and avoids duplicate initialization
    when a font of the same name already exists.

    :param args: Positional arguments to the Font constructor.
    :param kwargs: Keyword arguments to the Font constructor.
    :raises RuntimeError: If patch reference is broken or not defined.
    :return: None
    """

    global __ORIGINAL
    if __FONT_MANAGER_INITIALISED:
        # check if font exists. if exists, don't do stuff
        if "name" in kwargs and not FontManager()._font_name_exists(kwargs["name"]):
            try:
                out = __ORIGINAL["Font"](*args, **kwargs)
            except KeyError as error:
                raise RuntimeError("The original function is not linked properly in '_ORIGINAL' in the font_manager.py\n",
                                   str(error))

            FontManager()._add_new_font(kwargs)
            return out
        else:
            # font exists, so don't double load it
            return kwargs["name"]
    else:
        try:
            out = __ORIGINAL["Font"](*args, **kwargs)
        except KeyError as error:
            raise RuntimeError("The original function is not linked properly in '_ORIGINAL' in the font_manager.py\n",
                               str(error))
    return out

def __nametofont(*args, **kwargs):
    """
    Replaces `tkinter.font.nametofont` with a ProxyFont version from FontManager.

    :param args: Positional args, where the first should be font name.
    :param kwargs: Keyword args; can also include the font name via `name`.
    :raises ValueError: If no font name is given.
    :return: ProxyFont instance or None if font is not found.
    """

    font_name = args[0] if args else kwargs.get("name")
    if not font_name:
        raise ValueError("Font name parameter needed in nametofont().")

    proxy = FontManager().get_font_by_name(font_name)
    if proxy:
        return proxy
    return None

def __patch() -> None:
    """
    Initializes monkey-patching of relevant ttkbootstrap and tkinter font methods.

    This ensures that internal font handling is intercepted and routed
    through FontManager.

    :return: None
    """


    global __PATCHED, __ORIGINAL
    if __PATCHED:
        return

    __ORIGINAL["Font"] = tkfont.Font
    __font.__doc__ = ("Updated docstring by font_manager:\n" + str(__font.__doc__ or "") +
                        "\n\nOriginal docstring:\n" + (__ORIGINAL["Font"].__doc__ or ""))
    tkfont.Font = __font

    __ORIGINAL["nametofont"] = tkfont.nametofont
    __nametofont.__doc__ = ("Updated docstring by font_manager:\n" + str(__nametofont.__doc__ or "") +
                      "\n\nOriginal docstring:\n" + (__ORIGINAL["nametofont"].__doc__ or ""))
    tkfont.nametofont = __nametofont

    __ORIGINAL["Style"] = tb.Style
    __style.__doc__ = ("Updated docstring by font_manager:\n" + str(__style.__doc__ or "") +
                        "\n\nOriginal docstring:\n" + (__ORIGINAL["Style"].__doc__ or ""))
    tb.Style = __style

    __ORIGINAL["Window"] = tb.Window
    __window.__doc__ = ("Updated docstring by font_manager:\n" + str(__window.__doc__ or "") +
                        "\n\nOriginal docstring:\n" + (__ORIGINAL["Window"].__doc__ or ""))

    tb.Window = __window

    __PATCHED = True

# used to call once on import the internal function
__patch()

class ProxyFont:
    """
    A lightweight proxy that mimics a tkinter Font object using internal font data.

    This class is used to expose a dictionary-based font as a usable object without
    needing to register it with tkinter.

    Attributes:
        name (str): The name identifier of the font.
        font_data (dict): Dictionary of font options (e.g., family, size, weight).
    """

    def __init__(self, name: str, dict_font_data: dict):
        """
        Initializes the proxy font with a name and font attribute dictionary.

        :param name: str (The name of the font)
        :param dict_font_data: dict (The dictionary containing font properties)
        :return: None
        """

        self.name = name
        self.font_data = dict_font_data.copy()

    def actual(self, option=None):
        """
        Returns either the full font data dictionary or a specific option value.

        :param option: str | None (The key to retrieve from font_data. If None, returns full copy.)
        :return: dict | Any (Font value if key is given, otherwise a copy of the entire font data)
        """

        if option is None:
            return self.font_data.copy()
        else:
            return self.font_data.get(option)

    def cget(self, option):
        """
        Retrieves the value of a specific font configuration key.

        :param option: str (The font option to retrieve)
        :return: Any (The value associated with the font option key, or None if not found)
        """

        return self.font_data.get(option)

    def configure(self, **kwargs):
        """
        Updates the internal font data with the provided key-value pairs.

        Accepts valid font keys and updates the font_data dictionary accordingly.
        Keys that are not recognized will raise an error.

        :param kwargs: dict (Font attributes to update, such as size or weight)
        :raises KeyError: If an unknown font key is provided
        :return: dict (Updated copy of the font data)
        """

        if not kwargs:
            return self.font_data.copy()
        accepted_keys = ("family", "size", "weight", "slant", "underline", "overstrike")
        for key in kwargs:
            if key not in accepted_keys:
                raise KeyError("The key '" + key + "' is not acceptable")
            else:
                self.font_data[key] = kwargs[key]

    def config(self, **kwargs):
        """
        Alias for `configure`. Supports tkinter-style shorthand.

        :param kwargs: dict (Font attributes to update)
        :return: dict (Updated copy of the font data)
        """

        return self.configure(**kwargs)

    def __str__(self):
        """
        Returns the font name when cast to a string.

        :return: str (The name of the font)
        """

        return self.name

    def __repr__(self):
        """
        Returns a debug-friendly string representation of the proxy font.

        :return: str (Formatted string including the font name)
        """

        return f"<ProxyFont {self.name}>"

class FontManager:
    """
    Manages global font definitions and lookup for ttkbootstrap-based applications.

    This singleton class is responsible for:
    - Intercepting and replacing the `Font` constructor.
    - Tracking default and custom font definitions.
    - Providing access to fonts by name via `ProxyFont`.

    Attributes:
        _instance (FontManager): Singleton instance.
    """
    # Todo: add thread safety

    _instance = None

    def __new__(cls, *args, **kwargs) -> 'FontManager':
        """
        Implements singleton pattern by returning the same instance on every call.

        :return: FontManager (Singleton instance)
        """

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        Initializes the FontManager if not already initialized.

        Sets up internal dictionaries for default and custom fonts,
        and preloads default font definitions using the patched constructor.
        """

        # values per dict:
        # "name" : {'family': 'Segoe UI', 'size': 9, 'weight': 'normal', 'slant': 'roman', 'underline': 0, 'overstrike': 0}
        if not hasattr(self, '_initialized'):

            self.__custom_font_dict: dict = {}
            self.__default_font_dict: dict = {}

            self._font = globals().get("__ORIGINAL")["Font"]
            self._nametofont = globals().get("__ORIGINAL")["nametofont"]

            self._font(name="TkDefaultFont", exists=True)
            for font_name in tkfont.names():
                self.__default_font_dict[font_name] = self._nametofont(font_name).actual()
            self._initialized: bool = True

    def _font_name_exists(self, font_name: str) -> bool:
        """
        Checks whether a font name exists in the default or custom font dictionaries.

        :param font_name: str (The name of the font to look up)
        :return: bool (True if font exists, else False)
        """

        if font_name in self.__default_font_dict:
            return True
        if font_name in self.__custom_font_dict:
            return True
        return False

    def get_font_by_name(self, font_name: str) -> ProxyFont | None:
        """
        Retrieves a `ProxyFont` instance by font name if it exists.

        Checks the internal font dictionaries (default and custom) for the given font name
        and returns a proxy object that mimics a tkinter-compatible font.

        :param font_name: str (The name of the font to retrieve)
        :return: ProxyFont | None (A proxy font object if found, otherwise None)
        """

        if font_name in self.__default_font_dict:
            out_font_dict = self.__default_font_dict[font_name]
        elif font_name in self.__custom_font_dict:
            out_font_dict = self.__custom_font_dict[font_name]
        else:
            return None
        proxy_out = ProxyFont(name=font_name, dict_font_data=out_font_dict)
        return proxy_out

    def _add_new_font(self, font_data: dict):
        """
        Adds a new font entry to the internal custom font dictionary if it doesn't already exist.

        This method ensures that only fonts not already present in the internal registry
        are added, using the `name` field from the input dictionary as the key.

        :param font_data: dict (Dictionary containing font attributes, including the "name" key)
        :return: None
        """

        if not self._font_name_exists(font_data["name"]):
            self.__custom_font_dict[font_data.pop("name")] = font_data



