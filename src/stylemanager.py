"""
Provides a `StyleManager` class for ttkbootstrap that ensures consistent style management across themes.

This module wraps and extends the default ttkbootstrap `Style` class to support theme-safe style persistence.
Unlike the original behavior, it prevents styles from being lost after theme switches by automatically
re-registering them. It also supports a flexible pattern-based system for dynamically resolving
font, color, and geometry values based on widget and theme context.

Use `.register_style(...)` to define styles instead of calling `Style().configure(...)` directly.

Important:
- Call `StyleManager(root)` once after creating the root window.
- All styles must be assigned using `widget.config(style="YourStyle.Widget")`.

Author: sora_7672
"""
__author__ = "sora_7672"


import ttkb_eventinjector
import font_manager
import ttkbootstrap as tb
import tkinter as tk
from tkinter import font as tkfont

import copy
import inspect
from warnings import warn
from datetime import datetime, timedelta


# # # # Helper Functions # # # #
def is_hex(ins: str) -> bool:
    """
    Checks if a string is a valid hexadecimal color code (e.g., "#FFAA00").

    A valid hex color must:
    - be a string starting with "#"
    - contain exactly six hexadecimal characters afterwards

    :param ins: str (The input string to validate.)
    :return: bool (True if valid hex color, False otherwise.)
    """

    if (not isinstance(ins, str) or ins[0] != "#" or len(ins) != 7 or
            not all(c in "0123456789abcdefABCDEF" for c in ins[1:])):
        return False
    else:
        return True


# # # # Wrapper injection functions # # # #
# Injecting the wrappers into ttkbootstrap to have the developer not accidentally use the "old" methods from ttkb
if not globals().get("__PATCHED", False):
    __PATCHED = False
    __ORIGINAL = {}
    __STYLE_OBJECT = None


def __configure(*args, **kwargs):
    """
    Intercepts `Style.configure` to warn if used directly from outside `ttkbootstrap`.

    If called from external user code, a warning is issued. If called from within ttkbootstrap,
    the original `Style.configure` method is invoked.

    :param args: Positional arguments passed to `Style.configure`.
    :param kwargs: Keyword arguments passed to `Style.configure`.
    :return: Any (The result of the original `Style.configure` if allowed.)
    """

    global __ORIGINAL
    stack = inspect.stack()
    called_from_ttkb = any("ttkbootstrap" in frame.filename for frame in stack)

    if not called_from_ttkb:
        warn("Please don't use the ttkbootstrap Style().configure methode.\n"
             "Use the StyleManager().register_style methode instead.", UserWarning)
    else:
        out = __ORIGINAL["Style.configure"](*args, **kwargs)
        return out


def __map(*args, **kwargs):
    """
    Intercepts `Style.map` to warn if used directly from outside `ttkbootstrap`.

    Same behavior as `__configure`. Blocks usage from external files with a warning,
    but permits it internally from ttkbootstrap itself.

    :param args: Positional arguments passed to `Style.map`.
    :param kwargs: Keyword arguments passed to `Style.map`.
    :return: Any (The result of the original `Style.map` if allowed.)
    """

    global __ORIGINAL
    stack = inspect.stack()
    called_from_ttkb = any("ttkbootstrap" in frame.filename for frame in stack)

    if not called_from_ttkb:
        warn("Please don't use the ttkbootstrap Style().map methode.\n"
         "Use the StyleManager().register_style methode instead.",UserWarning)
    else:
        out = __ORIGINAL["Style.map"](*args, **kwargs)
        return out


def __wrap_style_methods() -> None:
    """
    Replaces `Style.configure` and `Style.map` with validation wrappers.

    Wraps both methods to inject runtime usage warnings and replaces their docstrings
    to clarify their intended use via the `StyleManager`.

    :return: None
    """

    global __ORIGINAL, __STYLE_OBJECT
    __ORIGINAL["Style.configure"] = __STYLE_OBJECT.configure
    __configure.__doc__ = ("Updated docstring by stylemanager:\n" + str(__configure.__doc__ or "") +
                       "\n\nOriginal docstring:\n" + (__ORIGINAL["Style.configure"].__doc__ or ""))
    __STYLE_OBJECT.configure = __configure

    __ORIGINAL["Style.map"] = __STYLE_OBJECT.map
    __map.__doc__ = ("Updated docstring by stylemanager:\n" + str(__map.__doc__ or "") +
                       "\n\nOriginal docstring:\n" + (__ORIGINAL["Style.map"].__doc__ or ""))
    __STYLE_OBJECT.map = __map


def __style(*args, **kwargs) -> tb.Style:
    """
    Patched constructor for `ttkbootstrap.Style`, returns a singleton instance.

    Ensures that only one `Style` instance is used across the application.
    If it doesn't exist yet, it creates one and wraps sensitive methods with
    developer warnings.

    :raises RuntimeError: If the original `Style` reference isn't available.
    :return: Style (The patched singleton Style instance.)
    """

    global __ORIGINAL, __STYLE_OBJECT
    if __STYLE_OBJECT is None:
        try:
            out = __ORIGINAL["Style"](*args, **kwargs)

        except KeyError as error:
            raise RuntimeError(
                "The original function is not linked properly in '_ORIGINAL' in the ttkb_eventinjector.py\n",
                str(error))
        __STYLE_OBJECT = out
        # need to first init standard themes, otherwise tb runs the config from internal once, which is not wanted
        # used_theme = out.theme_use()
        # for theme_name in out.theme_names():
        #     out.theme_use(theme_name)
        # out.theme_use(used_theme)

        if "Style.configure" not in __ORIGINAL:
            __wrap_style_methods()
        return out
    else:
        return __STYLE_OBJECT


def __patch() -> None:
    """
    Replaces `ttkbootstrap.Style` with a singleton wrapper version.

    This patch prevents developers from accidentally creating multiple `Style` objects,
    as all objects share the same underlying state.

    Should be called once during initialization to activate protection.

    :return: None
    """

    global __PATCHED, __ORIGINAL
    if __PATCHED:
        return

    __ORIGINAL["Style"] = tb.Style
    __style.__doc__ = ("Updated docstring by stylemanager:\n" + str(__style.__doc__ or "") +
                        "\n\nOriginal docstring:\n" + (__ORIGINAL["Style"].__doc__ or ""))
    tb.Style = __style

    __PATCHED = True


# used to call once on import the internal function
__patch()


# # # # main class for this module # # # #
class StyleManager:
    """
    A singleton style handler that manages dynamic, theme-persistent style creation in ttkbootstrap.

    This class:
    - Prevents styles from being overwritten or lost during theme changes.
    - Provides pattern-based substitution for dynamic font, color, and geometry resolution.
    - Injects wrappers to block direct `Style.configure()`/`map()` usage by developers.
    - Ensures consistency across all widgets and themes.

    Call `StyleManager(root)` once after initializing your root window and before calling `mainloop()`.

    Attributes:
        _instance (StyleManager): Singleton instance.
        __list_of_custom_styles (list[dict]): All registered styles.
        __list_of_custom_themes (list[dict]): All registered themes.
        __dict_style_theme_created (dict[str, list[str]]): Tracks which themes each style was created in.
        warn_on_duplicate (bool): If True, emits warning on duplicate styles.
        warn_on_override (bool): If True, emits warning on style override.
        bp_pattern (str): Expected syntax for placeholder patterns.
    """
    _instance = None

    __color_widget_target_keys = {'background', 'foreground', 'bordercolor', 'lightcolor', 'darkcolor', 'arrowcolor',
                                  'focuscolor', 'selectbackground', 'selectforeground', 'fieldbackground',
                                  'troughcolor', 'indicatorcolor'}
    __theme_color_sources = {'primary', 'secondary', 'success', 'info', 'warning', 'danger', 'light', 'dark', 'bg',
                             'fg', 'selectbg', 'selectfg', 'border', 'inputfg', 'inputbg', 'active'}
    __all_color_targets = set(list(__color_widget_target_keys) + list(__theme_color_sources))

    __widget_color_key_to_theme_key_map = {"background": "bg",
                                           "foreground": "fg",
                                           "bordercolor": "border",
                                           "lightcolor": "light",
                                           "darkcolor": "dark",
                                           "selectbackground": "selectbg",
                                           "focuscolor": "selectfg", "selectforeground": "selectfg",
                                           "arrowcolor": "fg",
                                           "fieldbackground": "inputbg",
                                           "troughcolor": "bg",
                                           "indicatorcolor": "primary"}
    __color_theme_to_widget_map = {"bg": "background", "primary": "background",
                                   "fg": "foreground", "inputfg": "foreground",
                                   "border": "bordercolor", "secondary": "bordercolor",
                                   "light": "lightcolor",
                                   "dark": "darkcolor",
                                   "inputbg": "fieldbackground",
                                   "selectbg": "selectbackground",
                                   "selectfg": "focuscolor"}

    __font_keys = {'family', 'size', 'style'}

    __geometry_keys = {'padding', 'borderwidth', 'relief', 'anchor', 'justify', 'width', 'height'}

    __font_and_widget_keys = {'TLabel', 'TButton', 'TCheckbutton', 'TRadiobutton', 'TMenubutton', 'TNotebook.Tab',
                              'TkDefaultFont', 'TkTextFont', 'TkFixedFont', 'TkMenuFont', 'TkHeadingFont',
                              'TkCaptionFont', 'TkSmallCaptionFont', 'TkIconFont', 'TkTooltipFont'}
    __actual_font_names = {'TkDefaultFont', 'TkTextFont', 'TkFixedFont', 'TkMenuFont', 'TkHeadingFont', 'TkCaptionFont',
                           'TkSmallCaptionFont', 'TkIconFont', 'TkTooltipFont'}
    __state_keys = {'active', 'disabled', 'focus', 'pressed', 'selected', 'alternate', 'readonly', 'hover',
                    'background', 'invalid'}
    # 'background' Some rare special case on some widgets
    # 'invalid' only on validation styles

    # Extended state_keys with the negated variants
    __state_keys = set(list(__state_keys) + [f"!{s}" for s in __state_keys])

    __widget_keys = {'TButton', 'TCheckbutton', 'TCombobox', 'TEntry', 'TFrame', 'TLabel', 'TLabelframe', 'TMenubutton',
                     'TNotebook', 'TNotebook.Tab', 'TPanedwindow', 'TProgressbar', 'TRadiobutton', 'TScale',
                     'TScrollbar', 'TSeparator', 'TSizegrip', 'TSpinbox', 'Treeview', 'Treeview.Heading'}

    __widget_init_map = {"TButton": tb.Button, "TCheckbutton": tb.Checkbutton, "TCombobox": tb.Combobox,
                         "TEntry": tb.Entry, "TFrame": tb.Frame, "TLabel": tb.Label, "TLabelframe": tb.Labelframe,
                         "TMenubutton": tb.Menubutton, "TNotebook": tb.Notebook, "TPanedwindow": tb.PanedWindow,
                         "TProgressbar": tb.Progressbar, "TRadiobutton": tb.Radiobutton, "TScale": tb.Scale,
                         "TScrollbar": tb.Scrollbar, "TSeparator": tb.Separator, "TSizegrip": tb.Sizegrip,
                         "TSpinbox": tb.Spinbox, "Treeview": tb.Treeview,
                         "TNotebook.Tab": None, "Treeview.Heading": None}
    # special cases will be inited in pattern resolver because sub element:
    # "TNotebook.Tab", "Treeview.Heading"

    def __new__(cls, *args, **kwargs) -> 'StyleManager':
        """
        Implements the singleton pattern by ensuring only one instance of the class exists.

        If no instance exists, it creates and returns a new one. Otherwise, it returns the existing instance.

        :return: StyleManager (The singleton instance)
        """

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self, tb_root: tb.Window = None) -> None:
        """
        Initializes the singleton `StyleManager` with a ttkbootstrap root window.

        This method ensures a single instance of the manager is created, binds to
        `<<PostThemeUse>>` to track theme changes, and prepares internal style registries.

        Must be called once with the root window reference before mainloop is started.

        :param tb_root: tb.Window (The root window instance of the application)
        :raises RuntimeError: If initialized more than once with a different root.
        :raises ValueError: If no `tb_root` is given on first initialization.
        :return: None
        """

        if hasattr(self, '_initialized'):
            if tb_root and tb_root != self.__root:
                raise RuntimeError("StyleManager already initialized with different root.\nThere can be only one!")
        if not hasattr(self, '_initialized'):
            if tb_root is None:
                raise ValueError('tb_root must be defined on first initialization')

            self._initialized = True
            self.__root = tb_root
            self.__list_of_custom_styles = []
            self.__list_of_custom_themes = []
            self.__dict_style_theme_created = {}
            # key = stylename, value = list[str,...] all themes where it got created.
            self.__root.bind_all("<<PostThemeUse>>", self._on_theme_change)
            self.__custom_warn_function = None
            self.warn_on_duplicate = False
            self.warn_on_override = True
            self.bp_pattern = "'$<type>[.<property>][#<widget>][?<modifiers>]'"

    def set_custom_warn_function(self, function_call):
        """
        Allows the developer to inject a custom warning handler.

        This can be used to reroute internal warnings (e.g., about incorrect style/theme usage)
        to a logging system, GUI notifier, or other custom handler.

        :param function_call: Callable (The function that will be called to issue warnings.)
        :return: None
        """

        self.__custom_warn_function = function_call

    def __get_style_object(self):
        """
        Retrieves the global ttkbootstrap `Style` object, creating it if necessary.

        This ensures consistent use of a single `Style` instance across the application.
        Used internally by the StyleManager.

        :return: Style (The singleton `Style` instance.)
        """

        style = globals().get("__STYLE_OBJECT")
        if style is None:
            style = tb.Style()
        return style
    def _on_theme_change(self, event=None):
        """
        Triggered after the active theme is changed to reapply all custom styles.

        This method ensures all registered custom styles are present in the new theme.
        If any are missing, they are reconstructed using internal helpers.

        :param event: Optional[Any] (The bound event from `<<PostThemeUse>>`.)
        :return: None
        """

        for custom_style in self.__list_of_custom_styles:
            if self.__is_style_created_in_current_theme(custom_style["style_name"]):
                continue
            else:
                style_to_create = self.__resolve_placeholder_dict(copy.deepcopy(custom_style))
                self.create_style(style_to_create)

    def __create_pseudo_font_dict(self, font_tuple: tuple | list) -> dict:
        """
        Generates a font configuration dictionary from a tuple or list representing a font.

        This method extracts the `family`, `size`, and optional styles (e.g., "bold", "italic") from the input
        and builds a normalized font dictionary usable in ttk styling logic. It also fills in any missing font
        attributes with safe defaults.

        :param font_tuple: tuple | list (Font specification as a tuple or list, e.g., ("Arial", 10, "bold italic"))
        :raises TypeError: If the font_tuple is not a tuple or list.
        :return: dict (A normalized dictionary containing font parameters for use with ttkbootstrap.)
        """
        if not isinstance(font_tuple, (tuple, list)):
            raise TypeError(f"Expected a tuple or list, got {type(font_tuple)}")
        extra_style_dict = {}
        if len(font_tuple) >= 3:
            extra_styles = font_tuple[2].lower().split(" ")
            for extra in extra_styles:
                match extra:
                    case "bold":
                        extra_style_dict["weight"] = "bold"
                    case "italic":
                        extra_style_dict["slant"] = "italic"
                    case "underline":
                        extra_style_dict["underline"] = 1
                    case "overstrike":
                        extra_style_dict["overstrike"] = 1

        pseudo_font_dict = {"family":font_tuple[0], "size": font_tuple[1], **extra_style_dict}
        default_styles = {'weight': 'bold', 'slant': 'roman', 'underline': 0, 'overstrike': 0}
        for def_key, def_value in default_styles.items():
            if def_key not in pseudo_font_dict:
                pseudo_font_dict[def_key] = def_value
        return pseudo_font_dict

    def __font_tuple_to_font(self, font_name: str, font_tuple: tuple | list):
        """
        Creates a `tkinter.font.Font` object from a tuple and assigns it a name.

        This function parses the tuple into structured font properties (including bold/italic/etc.)
        and creates a real `Font` instance tied to a specific name.

        :param font_name: str (The name to assign to the font instance.)
        :param font_tuple: tuple (Tuple of the format (family, size, "optional styles").)
        :raises TypeError: If the font_tuple is not a tuple or list.
        :return: Font (The constructed tkinter font object.)
        """
        if not isinstance(font_name, str):
            raise TypeError(f"Expected a string, got {type(font_name)}")
        if not isinstance(font_tuple, (tuple, list)):
            raise TypeError(f"Expected a tuple or list, got {type(font_tuple)}")

        extra_style_dict = {}
        if len(font_tuple) >= 3:
            extra_styles = font_tuple[2].lower().split(" ")
            for extra in extra_styles:
                match extra:
                    case "bold":
                        extra_style_dict["weight"] = "bold"
                    case "italic":
                        extra_style_dict["slant"] = "italic"
                    case "underline":
                        extra_style_dict["underline"] = 1
                    case "overstrike":
                        extra_style_dict["overstrike"] = 1

        new_font = tkfont.Font(name=font_name, family=font_tuple[0], size=font_tuple[1], **extra_style_dict)
        return new_font

    def __resolve_placeholder_dict(self, non_resolved_dict: dict) -> dict | None:
        """
        Resolves a style definition dictionary that may contain placeholder patterns into fully evaluated values.

        This method supports both `.config` and `.mapconfig` entries and processes patterns
        like font or color references.
        It handles special cases like padding and font tuples and creates a new font object for resolved fonts based on
        the current theme and style name.

        :param non_resolved_dict: dict (The input dictionary that may contain unresolved placeholder patterns.)
        :return: dict | None (A fully resolved style dictionary, or None if input was invalid.)
        :raises TypeError: If `non_resolved_dict` is not a dictionary.
        :raises ValueError: If a placeholder can't be resolved correctly.
        """
        #
        # Reminder: font patterns allways resolve with a whole tuple as output.
        # The 'family', 'size' and 'style' options are accepted but not needed in current setup.
        # It will be placed positional (0=family, 1=size, 2=style).
        #
        if not isinstance(non_resolved_dict, dict):
            raise TypeError('non_resolved_dict must be a dict')
        if not non_resolved_dict:
            # if the dict is emtpy, we return and empty dict
            return {}
        if not non_resolved_dict["has_pattern"]:
            # if we don't have pattern in that style, save cpu
            if isinstance(non_resolved_dict["config"], dict) and "font" in non_resolved_dict["config"]:
                style = self.__get_style_object()
                font_name = style.theme_use() + "-" + non_resolved_dict["style_name"]
                # font is here a 'Font' whyever....
                n_font = self.__font_tuple_to_font(font_name=font_name, font_tuple=non_resolved_dict["config"]["font"])
                non_resolved_dict["config"]["font"] = n_font

            return non_resolved_dict

        output_dict = {}
        # here we have a full dict with name, config and mapconfig

        output_dict["style_name"] = non_resolved_dict["style_name"]

        cfg = {}
        #config to filled config
        for config_key, config_value in non_resolved_dict["config"].items():
            # edgecase padding, that can have a tuple with 2 value as value
            if config_key == "padding" and isinstance(config_value, tuple):
                # TODO: pattern resolver allways returns a tuple for padding,
                #  so we nedd to split it here to the fitting position (0 =[0], 1=[1])
                padding1, padding2 = config_value
                padding_out = []
                if isinstance(padding1, str):
                    padding_out.append(self.__pattern_to_value(padding1[0]))
                else:
                    padding_out.append(padding1)
                if isinstance(padding2, str):
                    padding_out.append(self.__pattern_to_value(padding2[1]))
                else:
                    padding_out.append(padding2)

                cfg[config_key] = tuple(padding_out)
            # edge case font that always has a tuple with min 2 entries
            elif config_key == "font":
                if isinstance(config_value, (tuple, list)):
                    tuple_to_font = []
                    for index, font_value in enumerate(config_value):

                        if isinstance(font_value, str):
                            font_new = self.__pattern_to_value(font_value)
                        else:
                            font_new = font_value
                        # We need to return the list/tuple here
                        if isinstance(font_new, tuple):
                            font_new = font_new[index]
                        tuple_to_font.append(font_new)
                    # tuple font end

                else:
                    if isinstance(config_value, str):
                        tuple_to_font = self.__pattern_to_value(config_value)
                    else:
                        tuple_to_font = config_value
                # font place on config
                # to prevent problems, we init a new font based on
                # '<themename>-<stylename>' where stylename is buildup like this: '<stylename>.<widgetname>'
                style = self.__get_style_object()
                font_name = style.theme_use() + "-" + non_resolved_dict["style_name"]

                n_font = self.__font_tuple_to_font(font_name=font_name, font_tuple=tuple(tuple_to_font))
                cfg[config_key] = n_font
            else:

                # get pattern out of it, can only be in strings
                if isinstance(config_value, str):
                    cfg[config_key] = self.__pattern_to_value(config_value)
                else:
                    cfg[config_key] = config_value

        output_dict["config"] = cfg

        mcfg = {}
        #mapconfig zu filled mapconfig
        for mapconfig_key, mapconfig_value_list in non_resolved_dict["mapconfig"].items():
            # !!! mapconfig_value = list of tuple
            mapconfig_value_list_new = []
            for mapconfig_value_element in mapconfig_value_list:
                state_string, single_in_value = mapconfig_value_element

                # edgecase padding, that can have a tuple with 2 value as value
                if mapconfig_key == "padding" and isinstance(single_in_value, tuple):
                    padding1, padding2 = single_in_value
                    padding_out = []
                    if isinstance(padding1, str):
                        padding_out.append(self.__pattern_to_value(padding1))
                    else:
                        padding_out.append(padding1)
                    if isinstance(padding2, str):
                        padding_out.append(self.__pattern_to_value(padding2))
                    else:
                        padding_out.append(padding2)

                    mapconfig_value_list_new.append(tuple([state_string, tuple(padding_out)]))
                # edge case font that always has a tuple with min 2 entries
                elif mapconfig_key == "font":
                    tuple_to_font = []
                    for index, font_value in enumerate(single_in_value):
                        match index:
                            case 0:
                                # family allways str
                                font_new = self.__pattern_to_value(font_value)
                            case 1:
                                # size int or str
                                if isinstance(font_value, str):
                                    font_new = self.__pattern_to_value(font_value)
                                else:
                                    font_new = font_value

                            case 2:
                                # style allways str
                                font_new = self.__pattern_to_value(font_value)
                            case _:
                                # all other elements, just ignore for now
                                # TODO: maybe add some stuff later here
                                font_new = font_value
                        tuple_to_font.append(font_new)
                    mapconfig_value_list_new.append(tuple([state_string, tuple_to_font.name]))
                else:
                    # get pattern out of it, can only be in strings
                    if isinstance(single_in_value, str):
                        single_out_value = self.__pattern_to_value(single_in_value)
                    else:
                        single_out_value = single_in_value
                    mapconfig_value_list_new.append(tuple([state_string, single_out_value]))

            mcfg[mapconfig_key] = mapconfig_value_list_new

        output_dict["mapconfig"] = mcfg
        return output_dict

    def __pattern_to_value(self, pattern_string: str):
        """
        Resolves a single placeholder pattern string into its final value.

        The supported pattern types are `$color`, `$font`, and `$geometry`.
        Each pattern can optionally include properties, widget context, and future modifiers.

        :param pattern_string: str (The placeholder string to resolve, starting with `$`)
        :return: Any (The resolved value based on the pattern type.)
        :raises TypeError: If `pattern_string` is not a string.
        :raises ValueError: If the pattern cannot be resolved or contains an unknown type.
        :raises NotImplementedError: If modifiers are used, which are not yet supported.
        """

        if not isinstance(pattern_string, str):
            raise TypeError('pattern_string must be a string')
        if not pattern_string.startswith("$"):
            # no pattern in string, so return the actual value (can happen that string values end here)
            return pattern_string
        else:
            # has pattern
            # $<type>[.<property>][#<widget>][?<modifiers>]
            # solve to parts as dict
            pattern_dict = self.__resolve_pattern_string_to_dict(pattern_string)

            match pattern_dict["type"]:

                case "color":
                    output_value = self.__resolve_color_pattern_dict(pattern_dict)
                case "font":
                    output_value = self.__resolve_font_pattern_dict(pattern_dict)
                case "geometry":
                    output_value = self.__resolve_geometry_pattern_dict(pattern_dict)
                case _:
                    raise ValueError(f'Something went wrong with the pattern dict! {pattern_string} '
                                     f'to {pattern_dict}')

        return output_value

    def __resolve_color_pattern_dict(self, pattern_dict: dict) -> str | int:
        """
        Resolves a parsed color pattern dictionary into an actual color value.

        Supports widget-bound color resolution and falls back to theme-wide color keys.
        Handles both custom mappings and default ttkbootstrap color names.

        :param pattern_dict: dict (Dictionary representing a parsed color pattern.)
        :return: str | int (The resolved color value.)
        :raises TypeError: If pattern_dict or its values are not strings.
        :raises ValueError: If required properties are missing or resolution fails.
        :raises NotImplementedError: If modifiers are provided in the pattern.
        """

        if not isinstance(pattern_dict, dict):
            raise TypeError('pattern_dict must be a dict')
        for value in pattern_dict.values():
            if value and not isinstance(value, str):
                raise TypeError('value must be a string')

        if not pattern_dict["property"]:
            raise ValueError(f'property {pattern_dict["property"]} is not defined but needed')

        output_value = None
        style = self.__get_style_object()
        widget_color_grab_failure = False
        if pattern_dict["widget"]:
            if pattern_dict["property"] in self.__color_theme_to_widget_map.keys():
                widget_color_key = self.__color_theme_to_widget_map[pattern_dict["property"]]
            elif pattern_dict["property"] in self.__color_widget_target_keys:
                widget_color_key = pattern_dict["property"]
            else:
                raise ValueError(f'Property {pattern_dict["property"]} is not accepted together with widget')

            output_value = style.lookup(pattern_dict["widget"], widget_color_key)
            if output_value == "" or output_value is None:
                widget_color_grab_failure = True

        if not pattern_dict["widget"] or widget_color_grab_failure:
            # no widget & fallback for widget has no special color
            if pattern_dict["property"] in self.__widget_color_key_to_theme_key_map.keys():
                theme_color_key = self.__widget_color_key_to_theme_key_map[pattern_dict["property"]]
            else:
                theme_color_key = pattern_dict["property"]

            output_value = getattr(style.colors, theme_color_key)

        if output_value is None or "":
            raise ValueError(f'Something went wrong with the pattern dict, because no output is generated!\n'
                             f'{pattern_dict} ')

        if pattern_dict["modifier"]:
            # TODO: modifier handling, modify output
            raise NotImplementedError("Sorry modifiers are not yet implemented")

        return output_value

    def __resolve_font_pattern_dict(self, pattern_dict: dict):
        """
        Resolves a parsed font pattern dictionary into either a full Font object or one of its properties.

        If a specific property like `family`, `size`, or `style` is requested, it returns only that.
        Otherwise, it returns the full font reference. Also handles widget-bound default font lookup.

        :param pattern_dict: dict (Dictionary representing a parsed font pattern.)
        :return: Any (The resolved font or one of its properties.)
        :raises TypeError: If the input dictionary or its values are invalid.
        :raises ValueError: If the widget is unknown or invalid.
        :raises NotImplementedError: If modifiers are provided in the pattern.
        """

        if not isinstance(pattern_dict, dict):
            raise TypeError('pattern_dict must be a dict')
        for value in pattern_dict.values():
            if value and not isinstance(value, str):
                raise TypeError('value must be a string')

        output_value = None

        font_name = None
        if pattern_dict["widget"]:
            if pattern_dict["widget"] in self.__actual_font_names:
                font_name = pattern_dict["widget"]
            else:
                # when it's a widget not a font default
                # TODO: refactor like the other widget creations with the list.
                match pattern_dict["widget"]:
                    case "TLabel":
                        check_widget = tb.Label(tk._get_default_root(), text="test", style="TLabel")
                        check_widget.place_forget()
                        font_name = check_widget.cget("font")
                        check_widget.destroy()

                    case "TButton":
                        check_widget = tb.Button(tk._get_default_root(), text="test", style="TButton")
                        check_widget.place_forget()
                        font_name = check_widget.cget("font")
                        check_widget.destroy()

                    case "TCheckbutton":
                        check_widget = tb.Checkbutton(tk._get_default_root(), text="test", style="TCheckbutton")
                        check_widget.place_forget()
                        font_name = check_widget.cget("font")
                        check_widget.destroy()

                    case "TRadiobutton":
                        check_widget = tb.Radiobutton(tk._get_default_root(), text="test", style="TRadiobutton")
                        check_widget.place_forget()
                        font_name = check_widget.cget("font")
                        check_widget.destroy()

                    case "TMenubutton":
                        check_widget = tb.Menubutton(tk._get_default_root(), text="test", style="TMenubutton")
                        check_widget.place_forget()
                        font_name = check_widget.cget("font")
                        check_widget.destroy()

                    case "TNotebook.Tab":
                        check_widget = tb.Label(tk._get_default_root(), text="tab-sim", style="TNotebook.Tab")
                        check_widget.place_forget()
                        font_name = check_widget.cget("font")
                        check_widget.destroy()

                    case _:
                        raise ValueError(f'Something with the pattern widget is wrong.\n'
                                         f'{pattern_dict["widget"]} - is not valid')

        if not font_name:
            #get default
            font_name = "TkDefaultFont"

        font_to_check = tkfont.nametofont(font_name)

        if pattern_dict["property"]:
            # get only specific property (family, size, style)
            if pattern_dict["property"] == "style":
                output_value = self.__font_to_style_string(font_to_check)
            else:
                output_value = font_to_check.cget(pattern_dict["property"])
        else:
            output_value = font_to_check
        # otherwise it sticks to be a tuple
        if pattern_dict["modifier"]:
            # TODO: modifier handling, modify output
            #  Reminder, here it can happen that the output is a font tuple!
            raise NotImplementedError("Sorry modifiers are not yet implemented")

        return output_value

    def __font_to_style_string(self, font_to_transform) -> str:
        """
        Converts a `tkinter.Font` instance into a style string representation.

        Supported style keys: bold, italic, underline, overstrike. Missing attributes are skipped.

        :param font_to_transform: Font (A tkinter font object to convert.)
        :return: str (A space-separated string of style attributes.)
        """

        all_font = font_to_transform.configure()
        string_out = ""
        string_out += "bold " if all_font["weight"] == "bold" else ""
        string_out += "italic " if all_font["slant"] == "italic" else ""
        string_out += "underline " if all_font["underline"] else ""
        string_out += "overstrike " if all_font["overstrike"] else ""
        return string_out.strip()

    def __resolve_geometry_pattern_dict(self, pattern_dict: dict):
        """
        Resolves a geometry pattern dictionary into the actual geometry value for a given widget.

        This includes properties such as `padding`, `width`, `anchor`, and others that affect widget layout.
        Special cases like `TNotebook.Tab` and `Treeview.Heading` are handled by creating temporary widgets
        to extract the necessary values via `.cget()` or `.column().get()`.

        :param pattern_dict: dict (A parsed dictionary describing the geometry pattern.)
        :return: Any (The resolved geometry value, often int, str, or tuple[int, int].)
        :raises TypeError: If `pattern_dict` or its values are not the correct types.
        :raises ValueError: If required keys are missing or the widget/property is unsupported.
        :raises NotImplementedError: If a modifier is used, which is not yet implemented.
        """

        # Info padding wll allways return the tuple, it will be handled/splitted properly in the upper methode tree
        # __geometry_keys = ['padding', 'borderwidth', 'relief', 'anchor', 'justify', 'width', 'height']
        # TODO: test & implement all geometry keys, some are just placeholders right now
        if not isinstance(pattern_dict, dict):
            raise TypeError('pattern_dict must be a dict')
        for value in pattern_dict.values():
            if value and not isinstance(value, str):
                raise TypeError('value must be a string')

        if "widget" not in pattern_dict or not pattern_dict["widget"]:
            raise ValueError(f"pattern dict needs to have a valid widget for geometry patterns! {pattern_dict}")
        if "property" not in pattern_dict or not pattern_dict["property"]:
            raise ValueError(f"pattern dict needs to have a valid property for geometry patterns! {pattern_dict}")

        if pattern_dict["widget"] not in self.__widget_init_map:
            raise ValueError(f'pattern_dict widget is not supported! {pattern_dict["widget"]}')

        output_value = None
        if pattern_dict["widget"] == "TNotebook.Tab":
            # edgecase where we need to init the TNotebook first
            note_book = tb.Notebook(tk._get_current_root())
            note_book.place_forget()
            first_tab = note_book.tabs()[0]
            check_widget = note_book.nametowidget(first_tab)
            output_value = check_widget.cget(pattern_dict["property"])
            note_book.destroy()

        elif pattern_dict["widget"] == "Treeview.Heading":
            # edgecase where we need to init the Treeview first
            tree_view = tb.Treeview(tk._get_current_root(), columns=("col1",))
            tree_view.heading("col1", text="Test")
            tree_view.place_forget()
            output_value = tree_view.column("col1").get(pattern_dict["property"])
            tree_view.destroy()
        else:
            check_widget = self.__widget_init_map[pattern_dict["widget"]](tk._get_default_root())
            check_widget.place_forget()
            output_value = check_widget.cget(pattern_dict["property"])
            check_widget.destroy()

        if pattern_dict["modifier"]:
            # TODO: modifier handling, modify output
            #  reminder here it can happen to be a tuple for padding (int,int)
            #  on padding modify both values!
            raise NotImplementedError("Sorry modifiers are not yet implemented")

        if pattern_dict["property"] == "padding" and not isinstance(output_value, (tuple, list)):
            # edge case, needs to return a tuple of 2 values, even if just one is grabbed
            # need to check how to implement properly after all done here
            output_value = (output_value, output_value)

        return output_value

    def __resolve_pattern_string_to_dict(self, pattern_string: str) -> dict:
        """
        Parses a raw pattern string into a structured dictionary format.

        Pattern strings follow the format: `$<type>[.<property>][#<widget>][?<modifier>]`, where:
        - `<type>` is one of: font, color, geometry
        - `<property>` is an optional sub-attribute (e.g., size, background)
        - `<widget>` optionally restricts the resolution context
        - `<modifier>` is reserved for future transformation instructions

        :param pattern_string: str (The raw pattern string starting with `$`)
        :return: dict (A dictionary with keys: type, property, widget, modifier.)
        :raises TypeError: If `pattern_string` is not a string.
        :raises ValueError: If no valid type is detected in the string.
        """

        if not isinstance(pattern_string, str):
            raise TypeError('pattern_string must be a string')
        pattern_dict = {"type": None, "property": None, "widget": None, "modifier": None}

        # remove the $
        resolved_string = pattern_string[1:]

        # check for type and remove
        if resolved_string.startswith("font"):
            pattern_dict["type"] = "font"
            resolved_string = resolved_string[4:]
        elif resolved_string.startswith("color"):
            pattern_dict["type"] = "color"
            resolved_string = resolved_string[5:]

        elif resolved_string.startswith("geometry"):
            pattern_dict["type"] = "geometry"
            resolved_string = resolved_string[8:]

        else:
            raise ValueError(f"There is no valid type in {pattern_string}")

        had_dot = False
        if resolved_string.startswith("."):
            had_dot = True
            resolved_string = resolved_string[1:]

        has_widget = "#" in resolved_string
        has_modifier = "?" in resolved_string
        if had_dot:
            if has_widget or has_modifier:
                if has_widget and has_modifier:
                    # double split
                    pattern_dict["property"], resolved_string = resolved_string.split("#")
                    pattern_dict["widget"], pattern_dict["modifier"] = resolved_string.split("?")
                elif has_widget:
                    pattern_dict["property"], pattern_dict["widget"] = resolved_string.split("#")
                elif has_modifier:
                    pattern_dict["property"], pattern_dict["modifier"] = resolved_string.split("?")
            else:
                pattern_dict["property"] = resolved_string
        else:
            # no property
            # can have widget & modifier
            if resolved_string:
                if (has_widget := "#" in resolved_string) or (has_modifier := "?" in resolved_string):
                    if has_widget and has_modifier:
                        # double split
                        resolved_string = resolved_string[1:]  # remove '#'
                        pattern_dict["widget"], pattern_dict["modifier"] = resolved_string.split("?")
                    elif has_widget:
                        pattern_dict["widget"] = resolved_string[1:]  # remove '#'
                    elif has_modifier:
                       pattern_dict["modifier"] = resolved_string[1:]  # remove '?'

        return pattern_dict

    # # # # STYLES # # # #
    def create_style(self, custom_style: dict) -> None:
        """
        Creates and registers a new style in the current ttkbootstrap theme.

        This method uses `Style.configure` and `Style.map` to register the style definition.
        It also updates the internal registry to keep track of which themes the style has been created for,
        avoiding redundant creation when switching themes.

        :param custom_style: dict (A dictionary with keys `style_name`, `config`, and `mapconfig` defining the style.)
        :return: None
        :raises TypeError: If `custom_style` is not a dictionary.
        """

        if not isinstance(custom_style, dict):
            raise TypeError('custom_style must be a dict')

        style = self.__get_style_object()
        original = globals().get("__ORIGINAL")
        original["Style.configure"](custom_style["style_name"], **custom_style["config"])
        original["Style.map"](custom_style["style_name"], custom_style["mapconfig"])

        current_theme = style.theme_use()  # get theme string
        if custom_style["style_name"] in self.__dict_style_theme_created:
            themes_that_have_this_style = self.__dict_style_theme_created[custom_style["style_name"]]
            if current_theme not in themes_that_have_this_style:
                new_theme_list = themes_that_have_this_style + [current_theme]
                self.__dict_style_theme_created[custom_style["style_name"]] = new_theme_list
        else:
            self.__dict_style_theme_created[custom_style["style_name"]] = [current_theme]

    def __is_style_created_in_current_theme(self, style_name: str) -> bool:
        """
        Checks if a given style has already been created in the currently active theme.

        This is useful to avoid re-registering styles when switching themes, since styles are theme-specific.

        :param style_name: str (The name of the style to check.)
        :return: bool (True if the style exists for the current theme, False otherwise.)
        :raises TypeError: If `style_name` is not a string.
        """
        if not isinstance(style_name, str):
            raise TypeError('style_name must be a str')

        style = self.__get_style_object()
        current_theme = style.theme_use()
        if style_name in self.__dict_style_theme_created:
            if current_theme in self.__dict_style_theme_created[style_name]:
                return True

        # all other cases means not existing
        return False

    def get_registered_custom_style(self, style_name: str) -> dict | None:
        """
        Retrieves a registered custom style definition by its name.

        This allows external consumers to fetch the full style dictionary that was registered earlier.
        If the style does not exist, `None` is returned.

        :param style_name: str (The name of the style to look up.)
        :return: dict | None (The matching style dictionary, or None if not found.)
        """

        for style_entry in self.__list_of_custom_styles:
            if style_entry.get("style_name") == style_name:
                return style_entry
        return None

    def __get_comparable_font_values(self, font_data) -> dict | str:
        """
        Normalizes font data into a comparable dictionary form for internal style validation.

        Accepts either a pattern string, a Font object, or a font tuple. If a pattern string is passed,
        it is returned directly. Font tuples are converted into a pseudo-dict using internal rules.
        Fonts are converted using their `.config()` method.

        :param font_data: Any (Font string, tuple or Font object to normalize.)
        :return: dict | str (A dictionary of font properties or the original pattern string.)
        :raises TypeError: If conversion fails or the input type is invalid.
        """

        if isinstance(font_data, str) and font_data.startswith("$"):
            # if its a pattern, we dont change it
            return font_data
        out_dict = None
        if not isinstance(font_data, tuple):
            # no tuple = Font, we cant test for font properly.
            out_dict = font_data.config()
        if isinstance(font_data, tuple):
            # if tuple we need to make it to a pseudofont dict to compare
            out_dict = self.__create_pseudo_font_dict(font_data)
        if not isinstance(out_dict, dict):
            raise TypeError('Something went wrong in converting font/tuple to font dict:', font_data)
        return out_dict

    def __compare_styles(self, existing_style: dict, new_style: dict) -> bool:
        """
        Compares two style definitions and checks for full equality in both config and mapconfig sections.

        This method performs a deep comparison of two style dictionaries. Font values are normalized via
        `__get_comparable_font_values()` to ensure consistent comparison across patterns, tuples, and `Font` instances.

        - If any value differs in `config` or `mapconfig`, the function returns False.
        - Font values are compared using normalized pseudo-dictionaries.

        :param existing_style: dict (The first style dictionary to compare.)
        :param new_style: dict (The second style dictionary to compare.)
        :return: bool (True if the styles are identical in config and mapconfig, else False.)
        """

        for key in existing_style["config"].keys():

            if key == "font":
                # need to retranslate to font tuple and font to the same testable object
                existing_font = self.__get_comparable_font_values(existing_style["config"][key])
                new_font = self.__get_comparable_font_values(new_style["config"][key])
                # compare pseudo font dicts:
                if existing_font != new_font:
                    return False
            else:
                if existing_style["config"][key] != new_style["config"][key]:
                    return False

        existing_map = existing_style.get("mapconfig") or {}
        new_map = new_style.get("mapconfig") or {}
        ex_len = len(existing_map)

        if ex_len != len(new_map):
            return False
        elif ex_len > 0:
            for key in existing_map.keys():
                # special check for 'font' key
                if key == "font":
                    if "font" not in new_map:
                        return False

                    font_list_existing = []
                    for list_element in existing_map["font"]:
                        font_list_existing.append((list_element[0], self.__get_comparable_font_values(list_element[1])))

                    font_list_new = []
                    for list_element in new_map["font"]:
                        font_list_new.append((list_element[0], self.__get_comparable_font_values(list_element[1])))

                    if sorted(font_list_existing) != sorted(font_list_new):
                        return False

                # all other keys
                if key not in new_map or sorted(existing_map[key]) != sorted(new_map[key]):
                    return False
        # only return true if all are the same
        return True

    def register_style(self, style_name: str, config: dict, mapconfig: dict = None):
        """
        Registers a new style with the given name, configuration, and optional state-specific mapconfig.

        This method validates the style name, widget type, config, and mapconfig. If the style is already registered,
        it will either warn about duplicates or override depending on flags. If placeholders are used (patterns),
        they will be resolved before applying the style via `create_style()`.

        A style name must include a valid ttk widget (e.g., `"Custom.TButton"`).

        :param style_name: str (The name of the style to register, must include widget type.)
        :param config: dict (Style configuration, may include font and other visual options.)
        :param mapconfig: dict (Optional style mapping configuration for widget states.)
        :raises TypeError: If input types are invalid.
        :raises ValueError: If style name format or widget type is incorrect.
        :return: None
        """

        if not isinstance(style_name, str):
            raise TypeError('style_name must be a str')
        if not isinstance(config, dict):
            raise TypeError('config must be a dict')
        if mapconfig and not isinstance(mapconfig, dict):
            raise TypeError('mapconfig must be a dict')

        # Name check
        if "." not in style_name:
            raise ValueError("style_name must include the widget name.\n'<StyleName>.<WidgetName>'")

        widget_type = style_name.split(".")[-1]

        if widget_type not in self.__widget_keys:
            raise ValueError("style_name must include a valid widget name.\n'<StyleName>.<WidgetName>'\n" +
                             str(self.__widget_keys))

        # Config check, if wrong values are in it, it raises an error
        has_pattern = self.__validate_config(config)

        # Mapconfig check, if wrong values are in it, it raises an error
        if mapconfig is not None:
            map_has_pattern = self.__validate_mapconfig(mapconfig)
            if map_has_pattern:
                has_pattern = True
        else:
            mapconfig = {}

        # add config to the list (append)
        new_style = {"style_name": style_name, "config": config, "mapconfig": mapconfig,
                     "has_pattern": has_pattern, "last_update": datetime.now()}
        existing_style = self.get_registered_custom_style(style_name)
        is_same = False


        if existing_style:
            # lazy check only all 4 seconds for overlapping style
            difference = new_style["last_update"] - existing_style["last_update"]
            if difference < timedelta(seconds=4):
                return

            is_same = self.__compare_styles(existing_style, new_style)

        if is_same:
            if self.warn_on_duplicate:
                warn_message = f"Please check your buildup. You initialized 2x the same style. Registered Style:\n" \
                            f"{existing_style}"
                if self.__custom_warn_function is not None:
                    self.__custom_warn_function(warn_message)
                else:
                    warn(warn_message, UserWarning )
            return

        if not is_same and existing_style:
            if self.warn_on_override:
                warn_message = f"Please check your buildup. You initialized 2x the same style name: {style_name}\n"\
                                 f"Registered Style:\n"\
                                 f"{existing_style}\n"\
                                 f"New Style that OVERRIDES th registered style:\n"\
                                 f"{new_style}"
                if self.__custom_warn_function is not None:
                    self.__custom_warn_function(warn_message)
                else:
                    warn(warn_message, UserWarning)
            self.__list_of_custom_styles.remove(existing_style)

        self.__list_of_custom_styles.append(new_style)
        style_to_create = self.__resolve_placeholder_dict(copy.deepcopy(new_style))
        # after this wehave a 'Font' object for creation
        self.create_style(style_to_create)

    # # # # # # validation methods style start # # # # #
    def __validate_config(self, config: dict) -> bool:
        """
        Validates a config dictionary used for styling and detects whether it contains pattern references.

        Each key-value pair is checked for structural correctness and supported value types.
        If a valid pattern string is detected (e.g. "$font.size"), the result will be marked accordingly.

        :param config: dict (Style configuration dictionary with keys such as 'font', 'background', or 'padding'.)
        :return: bool (True if at least one pattern reference was found, else False.)
        :raises TypeError: If config is not a dictionary.
        """
        #
        # Reminder: font patterns allways resolve with a whole tuple as output.
        # The 'family', 'size' and 'style' options are accepted but not needed in current setup.
        # It will be placed positional (0=family, 1=size, 2=style).
        #
        if not isinstance(config, dict):
            raise TypeError('config must be a dict')

        has_pattern = False
        for config_key, config_value in config.items():
            # check if key is accepted
            key_type = self.__validate_config_key(config_key)

            # check config value is accepted
            found_pattern = self.__validate_config_value(key_type=key_type, config_key=config_key,
                                                             config_value=config_value)
            if found_pattern:
                has_pattern = True

        return has_pattern

    def __validate_mapconfig(self, mapconfig: dict) -> bool:
        """
        Validates a mapconfig dictionary (state-based style variations) and detects pattern references.

        Each value is expected to be a list of tuples with a state string and corresponding value.
        This function checks syntax, state definitions, and value patterns.

        :param mapconfig: dict (Mapping of style properties to state-value lists.)
        :return: bool (True if at least one pattern was found, else False.)
        :raises TypeError: If mapconfig is not a dict or contains invalid structures.
        :raises ValueError: If the state definitions or structure are invalid.
        """
        if not isinstance(mapconfig, dict):
            raise TypeError('mapconfig must be a dict')

        has_pattern = False
        for map_key, map_value in mapconfig.items():
            # map_value example: [(str, value),(str, value),...]
            # check if key accepted
            key_type = self.__validate_config_key(map_key)

            if not isinstance(map_value, list):
                raise TypeError(f'map_value must be a list: {map_value}')

            for list_element in map_value:
                # gets each tuple pair in the list

                if not isinstance(list_element, tuple):
                    raise TypeError(f'map_key: {map_key} - list_element must be a tuple: {map_value}')
                # split to tuple to its logical components, state and value
                state_string, config_value = list_element

                # check if state is accepted
                if not isinstance(state_string, str):
                    raise TypeError(f'map_key: {map_key} - state_string (first index of list_element) '
                                    f'must be a str: {state_string}')
                # the state string can include a list of states seperated through " "
                state_list = state_string.split()
                if not all([state_key in self.__state_keys for state_key in state_list]):
                    raise ValueError(f"map_key: {map_key} - "
                                     f"Your state_string/state_list includes invalid values:\n{state_list}"
                                     f"\nAccepted values: {self.__state_keys}")

                # check if config value is accepted
                # function as in config check
                found_pattern = self.__validate_config_value(key_type=key_type, config_key=map_key,
                                                             config_value=config_value)
                # Only if a pattern was found, set the has value, no override through direct init
                # multiple times True doesn't matter, but if false is between it will create a edge case
                # with this we work safe
                if found_pattern:
                    has_pattern = True

        return has_pattern

    def __validate_config_key(self, config_key: str) -> str:
        """
        Determines the type of configuration key: color, font, or geometry.

        Used to direct value validation toward the correct handler based on the config key.

        :param config_key: str (The config key to classify, e.g. 'padding', 'font', 'background'.)
        :return: str (One of: "color", "font", "geometry".)
        :raises TypeError: If config_key is not a string.
        :raises ValueError: If the config_key is unsupported.
        """

        if not isinstance(config_key, str):
            raise TypeError('config_key must be a str')

        if config_key in self.__all_color_targets:
            return "color"
        elif config_key == "font":
            return "font"
        elif config_key in self.__geometry_keys:
            return "geometry"
        raise ValueError(f"Sorry this config key is not supported in 'StyleManager': {config_key}")

    # single value checks below
    def __validate_config_value(self, key_type: str, config_key: str, config_value) -> bool:
        """
        Delegates validation of a single config key-value pair depending on its key type.

        :param key_type: str (The detected type of the config key: "color", "font", or "geometry".)
        :param config_key: str (The key name being validated.)
        :param config_value: Any (The value assigned to that key.)
        :return: bool (True if the value contains a valid pattern, else False.)
        :raises TypeError: If key_type or config_key are not strings.
        :raises ValueError: If key_type is not supported.
        """

        if not isinstance(config_key, str):
            raise TypeError('config_key must be a str')
        if not isinstance(key_type, str):
            raise TypeError('key_type must be a str')

        found_pattern = False

        match key_type:

            case "color":
                found_pattern = self.__validate_config_value_color(config_key=config_key, config_value=config_value)
            case "font":
                found_pattern = self.__validate_config_value_font(config_key=config_key, config_value=config_value)
            case "geometry":
                found_pattern = self.__validate_config_value_geometry(config_key=config_key, config_value=config_value)
            case _:
                raise ValueError(f"Sorry this config type is not supported in 'StyleManager': {key_type}")
        return found_pattern

    def __validate_config_value_color(self, config_key: str, config_value: str) -> bool:
        """
        Validates color values, either as static hex values or pattern-based inputs.

        Accepts either standard hex codes (e.g., "#ffaa33") or pattern strings starting with `$color.`.

        :param config_key: str (The name of the config key being checked.)
        :param config_value: str (The value assigned to that key.)
        :return: bool (True if the value is a pattern string, else False.)
        :raises TypeError: If inputs are not strings.
        :raises ValueError: If the pattern syntax or property is invalid.
        :raises NotImplementedError: If a modifier is used in the pattern.
        """

        if not isinstance(config_key, str):
            raise TypeError(f"config_key must be a str: {config_key}")
        if not isinstance(config_value, str):
            raise TypeError(f"config_key: {config_key} - is a color so config_value must be a str:"
                            f"{type(config_value)} {config_value}")
        found_pattern = False

        if config_value.startswith("$"):
            found_pattern = True

        if found_pattern:
            if not config_value[1:].startswith("color"):
                raise ValueError(f"Key: {config_key} - Your pattern start doesn't work for colors: "
                                 f"{config_value}\n"
                                 f"Accepted start value '$color.<property>'\n"
                                 f"{self.bp_pattern}")

            if not config_value[6] == ".":
                # Needs to know where to grab color from
                raise ValueError(f"Key: {config_key} - You dont have a property connector '.': {config_value}\n"
                                 f"{self.bp_pattern}")
            if not config_value[7:].startswith(tuple(self.__all_color_targets)):
                raise ValueError(f"Key: {config_key} - Your property is wrong: {config_value}\n"
                                 f"Accepted values after '$color.'\n"
                                 f"{self.__all_color_targets}\n"
                                 f"{self.bp_pattern}")
            # widget check
            if "#" in config_value:
                widget_id = config_value.split("#")[1]
                if not widget_id.startswith(tuple(self.__widget_keys)):
                    raise ValueError(f"Key: {config_key} - Your widget is not allowed for colors: {config_value}\n"
                                     f"{self.__widget_keys}\n"
                                     f"{self.bp_pattern}")
            # modifier check
            if "?" in config_value:
                raise NotImplementedError("Sorry the modifiers can't be used till now :'( ")

        else:
        # do value check
            if not is_hex(config_value):
                raise ValueError(f"This config key '{config_key}' has to be a hexdecimal color: {config_value}"
                                 f"\nIt needs to start with a # and have 6 chars from a to f or 0 to 9")

        # if reached here it's all valid
        return found_pattern

    def __validate_config_value_font(self, config_key: str, config_value: tuple) -> bool:
        """
        Validates font values, which must be tuples (family, size, style) or patterns.

        Each element in the font tuple is checked for correctness or resolved if it's a pattern.
        Patterns must follow the format: `$font.<property>[#<widget>]`.

        :param config_key: str (The config key name, expected to be "font".)
        :param config_value: tuple (Tuple representing the font: (family, size[, style, ...]))
        :return: bool (True if any element is a pattern, else False.)
        :raises TypeError: If the input types are incorrect.
        :raises ValueError: If tuple length or pattern syntax is invalid.
        :raises NotImplementedError: If modifiers are used in the pattern.
        """

        if not isinstance(config_key, str):
            raise TypeError(f"config_key must be a str: {config_key}")
        if not isinstance(config_value, tuple):
            raise TypeError(f"config_key: {config_key} - is a font so config_value must be a tuple: "
                            f"{type(config_value)} {config_value}")

        if len(config_value) < 2:
            raise ValueError(f"config_key: {config_key} - Font allways has to be a tuple of 2 entries or more.\n"
                             f"{config_value}")
        found_pattern = False

        for index, check_value in enumerate(config_value):
            # get index numbers and each element for checks

            # here we use is_pattern, to ensure to check on each element
            # the has_pattern can only be set true, never false
            is_pattern = False
            if isinstance(check_value, str):
                if check_value.startswith("$"):
                    is_pattern = True

            if is_pattern:
                found_pattern = True
                # do syntax check
                # type and property check
                if not check_value[1:].startswith("font"):
                    raise ValueError(f"Key: {config_key} - Your pattern start doesn't work for fonts: {check_value}\n"
                                     f"Accepted start value '$font.<property>'\n"
                                     f"{self.bp_pattern}")

                if len(check_value) > 5 and check_value[5] == ".":
                    # Optional, if not chosen will lookup default value
                    if not check_value[6:].startswith(tuple(self.__font_keys)):
                        raise ValueError(f"Key: {config_key} - Your property is wrong: {check_value}\n"
                                         f"Accepted values after '$font.'\n{self.__font_keys}\n"
                                         f"{self.bp_pattern}")
                # widget check
                if "#" in check_value:
                    # Optional, if not chosen will lookup default value
                    widget_id = check_value.split("#")[1]
                    if not widget_id.startswith(tuple(self.__font_and_widget_keys)):
                        raise ValueError(f"Key: {config_key} - Your widget is not allowed for fonts: {check_value}\n"
                                         f"{self.__font_and_widget_keys}\n"
                                         f"{self.bp_pattern}")
                # modifier check
                if "?" in check_value:
                    raise NotImplementedError("Sorry the modifiers can't be used till now :'( ")
            else:
                # do value check
                match index:
                    case 0:
                    # font family
                        if not isinstance(check_value, str):
                            raise TypeError(f"Key: {config_key} - First element(family) in a font tuple "
                                            f"has to be a str: {type(check_value)} {check_value}")
                    case 1:
                        # size
                        if not isinstance(check_value, int):
                            raise TypeError(f"Key: {config_key} - Second element(size) in a font tuple "
                                            f"has to be a int: {type(check_value)} {check_value}")
                    case 2:
                        # style "bold italic"
                        if not isinstance(check_value, str):
                            raise TypeError(f"Key: {config_key} - Third element(style) in a font tuple "
                                            f"has to be a str: {type(check_value)} {check_value}")
                    case _:
                        # other values that we don't test so far
                        # TODO: maybe later more in depth checks in fonts
                        pass

        # if reached here it's all valid
        return found_pattern

    def __validate_config_value_geometry(self, config_key: str, config_value) -> bool:
        """
        Validates geometry values such as padding, width, height, etc.

        Accepts static values (e.g., int or tuple) or pattern strings of the form `$geometry.<property>[#<widget>]`.
        For padding, two integers in a tuple are expected and validated separately.

        :param config_key: str (The geometry-related key to validate, e.g., 'padding'.)
        :param config_value: Any (The corresponding value to be validated.)
        :return: bool (True if a pattern was found, else False.)
        :raises TypeError: If input types are invalid.
        :raises ValueError: If syntax or range checks fail.
        :raises NotImplementedError: If unsupported geometry keys or modifiers are used.
        """

        if not isinstance(config_key, str):
            raise TypeError(f"config_key must be a str: {config_key}")
        found_pattern = False

        # check for edge case "padding"
        if config_key == "padding" and isinstance(config_value, tuple):
            check_value_list = list(config_value)
        else:
            check_value_list = [config_value]

            for check_value in check_value_list:
                # in case of tuple input it runs each element, in case of single input it runs 1x

                is_pattern = False
                if isinstance(check_value, str) and check_value.startswith("$"):
                    is_pattern = True

                if is_pattern:
                    found_pattern = True
                    # do syntax check
                    # type and property check
                    if not check_value[1:].startswith("geometry"):
                        raise ValueError(f"Key: {config_key} - Your pattern start doesn't work for geometry: {check_value}\n"
                                         f"Accepted start value '$geometry.<property>'\n"
                                         f"{self.bp_pattern}")

                    if not check_value[9] == ".":
                        # Needs to know from where to grab geometry data
                        raise ValueError(f"Key: {config_key} - You dont have a property connector '.': {check_value}\n"
                                         f"{self.bp_pattern}")

                    if not check_value[10:].startswith(tuple(self.__geometry_keys)):
                        raise ValueError(f"Key: {config_key} - Your property is wrong: {check_value}\n"
                                         f"Accepted values after '$geometry.'\n{self.__geometry_keys}\n"
                                         f"{self.bp_pattern}")
                    # widget check
                    if "#" in check_value:
                        # Optional, if not chosen will lookup default value
                        widget_id = check_value.split("#")[1]
                        if not widget_id.startswith(tuple(self.__widget_keys)):
                            raise ValueError(f"Key: {config_key} - Your widget is not allowed for geometry: {check_value}\n"
                                             f"{self.__widget_keys}\n"
                                             f"{self.bp_pattern}")
                    # modifier check
                    if "?" in check_value:
                        raise NotImplementedError("Sorry the modifiers can't be used till now :'( ")
                else:
                    # do value check
                    match config_key:
                        case "borderwidth" | "width" | "height" | "padding":
                            if not isinstance(check_value, int) or check_value < 0:
                                raise ValueError(
                                    f"This config key '{config_key}' has to be an int with positive value: "
                                    f"{type(check_value)} {check_value}")
                        case _:
                            # TODO: implement other font geometry checks
                            raise NotImplementedError("Sorry the maybe the geometry key exists, "
                                                      "but is not yet implemented :'( ")

        return found_pattern

    # # # # # # validation methods style end   # # # # #

    # # # # THEMES # # # #
    # NYI

    def register_theme(self, theme_name: str, theme_config: dict):
        """
        Registers a new theme configuration under a given name.

        :param theme_name: str (The name of the theme.)
        :param theme_config: dict (The configuration dictionary for the theme.)
        :raises NotImplementedError: Always, since the method is not yet implemented.
        """

        # TODO: Implement this
        raise NotImplementedError("Sorry not yet implemented. Maybe follows soon :(")

        if not isinstance(theme_name, str):
            raise TypeError(f"Theme must be a str: {type(theme_name)} {theme_name}")
        if not isinstance(theme_config, dict):
            raise TypeError(f"Theme must be a dict: {type(theme_config)} {theme_config}")

    def create_themes(self):
        """
        Applies and creates all registered theme definitions.

        :raises NotImplementedError: Always, since the method is not yet implemented.
        """

        # TODO: Implement this
        raise NotImplementedError("Sorry not yet implemented. Maybe follows soon :(")

    def exists_theme_name(self, theme_name: str) -> dict | None:
        """
        Checks if a theme with the given name has already been registered.

        :param theme_name: str (The name of the theme to check.)
        :return: dict | None (Theme config if it exists, otherwise None.)
        :raises NotImplementedError: Always, since the method is not yet implemented.
        """

        # TODO: Implement this
        raise NotImplementedError("Sorry not yet implemented. Maybe follows soon :(")

        if not isinstance(theme_name, str):
            raise TypeError(f"Theme must be a str: {type(theme_name)} {theme_name}")



if __name__ == "__main__":
    print("Don't start this module directly.")
