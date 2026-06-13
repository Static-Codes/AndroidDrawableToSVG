#################### Disabling Byte Code Generation ####################
import sys
sys.dont_write_bytecode = True






#################### Application Imports ####################
from getopt import getopt, GetoptError
from os import path
from re import compile, DOTALL, Pattern, RegexFlag, search, VERBOSE
from typing import Callable, Dict, List, Optional, Tuple
from xml.etree import ElementTree
from xml.etree.ElementTree import parse, ParseError, fromstring






#################### Constants #################### 

# The current release of ADAS (as it stands, this is a pre-release).
SCRIPT_VERSION: str = "v0.0.1-pre-release"

# Used for re.search
FLAGS: RegexFlag = VERBOSE | DOTALL

# The default/fallback value for fillColor="X" if it cannot be parsed/converted.
BLACK_HEX: str = "#000000"

# The regex pattern used by fc_is_already_hex()
# After multiple implementations, regex has been found to be more reliable than using base 16/32 conversion.
HEX_COLOR_PATTERN: Pattern = compile(r'^#([A-Fa-f0-9]{3}|[A-Fa-f0-9]{4}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$')

# The root namespace for the converted SVG file.
SVG_NAMESPACE: str = "http://www.w3.org/2000/svg"

ANDROID_NAMESPACE: str = "{http://schemas.android.com/apk/res/android}"

# Prefix strings used during color resolution of non-16-bit integers.
SDK_COLOR_PREFIX = "@android:color/"
USER_MADE_COLOR_PREFIX = "@color/"

# A collection of built-in color names from the Android SDK and their associated Hex Values.
# Pulled from https://developer.android.com/reference/android/graphics/Color#constants_1
# The alpha channels were removed for 16 bit integer compatibility.
GRAPHICS_COLOR_MAP: Dict[str, str] = {
    "black": BLACK_HEX,
    "blue": "#0000FF",
    "cyan": "#00FFFF",
    "dkgray": "#444444",
    "gray": "#888888",
    "green": "#00FF00",
    "ltgray": "#CCCCCC",
    "magenta": "#FF00FF",
    "red": "#FF0000",
    "transparent": "#00000000",
    "white": "#FFFFFF",
    "yellow": "#FFFF00"
}






#################### Required User Input ###################

# The path to the VectorDrawable XML file that will be converted.
DRAWABLE_XML_FILEPATH: Optional[str] = None

# The path to the SVG that will be written upon a successful conversion.
OUTPUT_SVG_FILEPATH: Optional[str] = None






####################  Optional User Input/States #################### 

# The path to the colors.xml file.
# This file contains a collection of color properties that may be used for more complex DrawableVector.
# 
# This collection is broken down as follows:
#   The property name (Resource ID) is the "name" attribute 
#   The property value is usually a Hex Value.

COLORS_XML_FILEPATH: Optional[str] = None


# The path to the strings.xml file.
# This file contains a collection of string resources that may be used for more complex DrawableVector.
# 
# This collection is broken down as follows:
#   The property name (Resource ID) is the "name" attribute 
#   The property value is usually Path Data.

STRINGS_XML_FILEPATH: Optional[str] = None

# This state variable is set to True if the flags "-c" or "--colors" are passed.
USING_COLOR_RESOURCES: bool = False

# This state variable is set to True if the flags "-s" or "--strings" are passed.
USING_STRING_RESOURCES: bool = False

# The map will be populated using COLORS_XML_FILE if USING_COLOR_RESOURCES is set to True.
COLOR_RESOURCES_MAP: Dict[str, str] = {}

# The map will be populated using STRINGS_XML_FILEPATH if USING_STRING_RESOURCES is set to True.
STRING_RESOURCES_MAP: Dict[str, str] = {}






################### Input Mutatation Functions ###################

def has_multiple_map_args(MAP_XML_FILEPATH: str) -> bool:
    """Returns True if MAP_XML_FILEPATH has multiple filepaths specified, otherwise False."""
    return ";" in MAP_XML_FILEPATH


def remove_angle_brackets(MAP_XML_FILEPATH: str) -> str:
    return MAP_XML_FILEPATH.removeprefix('<').removesuffix('>')


def set_color_resource_map() -> None:
    global COLOR_RESOURCES_MAP
    global COLORS_XML_FILEPATH


    # Removing the leading and trailing angle brackets ("<" and ">"), if present.
    COLORS_XML_FILEPATH = COLORS_XML_FILEPATH.lstrip('<').rstrip('>')

    resources: List[str]

    # Separating the resources if multiple were provided, otherwise creating a list with one element.
    if has_multiple_map_args(COLORS_XML_FILEPATH):
        resources = COLORS_XML_FILEPATH.split(";")
    else:
        resources = [COLORS_XML_FILEPATH]

    valid_resources = [res for res in resources if path.exists(res)]
    resources = None


    try:
        number_of_resources = len(valid_resources)

        if number_of_resources == 0:
            raise Exception("No valid resources were provided, please check your paths.")

        elif number_of_resources == 1:
            COLOR_RESOURCES_MAP = load_color_map_xml(valid_resources[0])
            return

        COLOR_RESOURCES_MAP = flatten_multiple_maps(COLOR_RESOURCES_MAP, valid_resources, load_color_map_xml)

    except Exception as e:
        print("[WARNING]: A fatal error occured while loading COLORS_XML_FILEPATH.")
        print(f"[ERROR]: {e}")
        exit(1)

        
def set_string_resource_map() -> None:
    global STRING_RESOURCES_MAP
    global STRINGS_XML_FILEPATH

    
    # Removing the leading and trailing angle brackets ("<" and ">")
    STRINGS_XML_FILEPATH = STRINGS_XML_FILEPATH.lstrip('<').rstrip('>')

    resources: List[str]

    # Separating the resources if multiple were provided, otherwise creating a list with one element.
    if has_multiple_map_args(STRINGS_XML_FILEPATH):
        resources = STRINGS_XML_FILEPATH.split(";")

    else:
        resources = [STRINGS_XML_FILEPATH]

    
    valid_resources = [res for res in resources if path.exists(res)]
    resources = None

    
    try:
        number_of_resources = len(valid_resources)

        if number_of_resources == 0:
            raise Exception("No valid resources were provided, please check your paths.")

        elif number_of_resources == 1:
            STRING_RESOURCES_MAP = load_string_map_xml(valid_resources[0])
            return

        STRING_RESOURCES_MAP = flatten_multiple_maps(STRING_RESOURCES_MAP, valid_resources, load_string_map_xml)
        

    except Exception as e:
        print("[WARNING]: A fatal error occured while loading STRING_RESOURCES_MAP.")
        print(f"[ERROR]: {e}")
        exit(1)


def flatten_multiple_maps(map_obj: Dict[str, str], resources: List[str], func: Callable[[str], Dict[str, str]]) -> Dict[str, str]:
    """Flattening each map into a single unified map."""
    for resource in resources:
        map_obj = map_obj | func(resource)
    return map_obj



#################### Formatting Helper Functions ####################   


def expand_fc_if_needed(fill_color: str) -> str:
    """
    If a fill_color is only 3 or 4 characters, it is missing one of each R, G, B, and potentially A (Alpha).
    An expanded fill_color will be returned if the length is 3 or 4, otherwise, the original value is returned.
    """
    if not fill_color.startswith("#"): 
        return fill_color
    
    length = len(fill_color)
    
    red: Optional[str] = None
    green: Optional[str] = None
    blue: Optional[str] = None
    alpha: Optional[str] = None

    # Expanding 3 char hex sequences to 6 char sequences.
    # "#RGB" -> "#RRBBGG"
    if length == 4:
        red = fill_color[1]
        green = fill_color[2]
        blue = fill_color[3]

        return f"#{red*2}{green*2}{blue*2}"

    # Expanding 4 char hex sequences to 8 char hex sequences
    # Noteably, this involves flipping the alpha channel, from the first two chars of the sequence to the last two.
    # Without this, previous implementations had transparency and color mismatching issues.
    # Pulled from: https://observablehq.com/@dralletje/android-xml-to-svg#cell-203
    elif length == 5:
        alpha = fill_color[1]
        red = fill_color[2]
        green = fill_color[3]
        blue = fill_color[4]

        return f"#{red*2}{green*2}{blue*2}{alpha*2}"

    # Much 4 char hex sequences, 8 char sequences also require alpha channel flipping.
    # There are other aspects of SVG compliance that were covered in the guide above, however, none apply here.
    elif length == 9:
        alpha = fill_color[1:3]
        red = fill_color[3:5]
        green = fill_color[5:7]
        blue = fill_color[7:9]

        return f"#{red}{green}{blue}{alpha}"

    # Falling back to original input, since it can't safely be expanded.
    return fill_color
    
def fc_has_color_reference(fill_color: str) -> bool:
    """Checks if the current fill color is a color reference, if so, additional resolution is required."""

    if not isinstance(fill_color, str):
        return False

    # Checking if a user defined color prefix is present.
    elif fill_color.startswith(USER_MADE_COLOR_PREFIX):
        return True

    # Checking if a built-in SDK color is present.
    elif fill_color.startswith(SDK_COLOR_PREFIX):
        return True

    return False
    

def fc_is_already_hex(fill_color: str) -> bool:
    """Checking if a hex sequence is valid PRIOR to any conversion attempts, ultimately to save cpu cycles."""
    return True if HEX_COLOR_PATTERN.fullmatch(fill_color) else False


def has_aosp_copyright(contents: str) -> bool:
    """Checking if the provided contents contains the Android Open Source Project (AOSP)'s Copyright."""
    PATTERN = r"Copyright\s+\(C\)\s+\d{4}.*?The\s+Android\s+Open\s+Source\s+Project"

    REGEX = compile(PATTERN, FLAGS)
    
    return REGEX.search(contents) is not None


def has_xml_header(contents: str) -> bool:
    """Checking if the provided contents contains the expected XML header attribute."""
    return contents.startswith('<?xml version="1.0" encoding="utf-8"?>')


def pd_has_string_reference(path_data: str) -> bool:
    """Checks if the current path data is a string reference, if so, additional resolution is required."""
    if not isinstance(path_data, str):
        return False

    return False if not path_data else "@string/" in path_data


def split_fc_if_needed(fill_color: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Takes a hex sequence string, if the string is not formatted as #RRGGBBAA, it is not modified.
    
    modified_hex: str | Contains #RRGGBB (if the condition above is met) or None.
    alpha_str | Contains a string representation of a decimal (float) ranging from 0.0 to 1.0 or None

    Returns either:
    - 1. Tuple[modified_hex, alpha_str]
    - 2. Tuple[fill_color, None]
    """

    length: int = len(fill_color)

    # Ensuring the color is in compliant format (#AARRGGBB) before continuing.
    if (not fill_color) or (not fill_color.startswith('#')) or (length != 9):
        return (fill_color, None)
    
    # Grabbing the alpha channel hex value (AA from #RRGGBBAA)
    raw_alpha_hex: str = fill_color[length - 2:]

    # Grabbing the first 7 chars in the sequence (#RRGGBB from #RRGGBBAA)
    modified_hex: str = fill_color[0:7]

    # Converting the alpha channel from hex to dec then returning its string representation.
    alpha_str: str = convert_alpha_hex_to_decimal_str(raw_alpha_hex)

    return (modified_hex, alpha_str)


def check_drawable_vector_format(drawable_vector_contents: str):
    """
    Both of the checks below are non-fatal and serve primarily for debugging purposes.
    
    It is entirely possible to parse a raw <vector>...</vector> however:
    
    The AOSP releases standardized DrawableVectors here:
    https://cs.android.com/androidx/platform/frameworks/support/+/androidx-main:vectordrawable/vectordrawable/src/androidTest/res/
    """
    
    if not has_xml_header(drawable_vector_contents):
        print(f"[WARNING]: The XML header is missing for: {DRAWABLE_XML_FILEPATH}")
        print("[WARNING]: This may impact the result of the current conversion.")
        print("[INFO]: Attempting to continue..")
    
    if not has_aosp_copyright(drawable_vector_contents):
        print("[WARNING]: The Android Open Source Project (AOSP) copyright was not located.")
        print("[WARNING]: This may impact the result of the current conversion.")
        print("[INFO]: Attempting to continue..")


def resolve_and_format_stroke_color(path_node: Dict[str, str]) -> str:
    """
    Extracts the strokeColor and Resolves associated color references, if present.
    Expands short hex sequences, if present.
    Returns the stroke color, if defined, otherwise, an empty string.
    """
    final_stroke_color = path_node.get("strokeColor")
    
    if not final_stroke_color:
        return ""
    
    if fc_has_color_reference(final_stroke_color):
        final_stroke_color = resolve_color_reference(final_stroke_color)
    
    final_stroke_color = expand_fc_if_needed(final_stroke_color)
    return f' stroke="{final_stroke_color}"'


def format_stroke_width(path_node: Dict[str, str]) -> str:
    """
    Extracts and sanitizes the strokeWidth attribute, if present. 
    Ensures the value is sanitized and represents a valid floating-point number.
    Returns an SVG compliant stroke-width attribute string, if valid, otherwise an empty string.
    """
    stroke_width = path_node.get("strokeWidth")

    if not stroke_width:
        return ""

    # Isolating the numeric portion of the stroke width string.
    # Converts "1.5dp" to "1.5", etc.
    sanitized_stroke_width = remove_units_from_numeric_string(stroke_width)

    # If the explicit float cast fails, then the value provided is not a valid width.
    try:
        float(sanitized_stroke_width)
        return f' stroke-width="{sanitized_stroke_width}"'
        
    except ValueError:
        print(f"[WARNING]: Invalid float format encountered for strokeWidth: '{stroke_width}'")
        print("[INFO]: Skipping stroke-width attribute for this path.")
        return ""






#################### File Parsing Functionality ####################


def load_drawable_vector_xml(drawable_vector_path: str) -> str:
    """Parses the DrawableVector XML and returns its contents as a string, or exits on an exception."""
    try:
        with open(drawable_vector_path, "r", encoding="utf-8") as file:
            return file.read()
    
    except Exception as e:
        print("An exception occured while trying to read the provided XML file.")
        print(f"Error: {e}")
        exit(1)



def load_color_map_xml(colors_xml_path: str) -> Dict[str, str]:
    """Parses colors.xml into a Dict[str, str] or exits on an exception."""
    
    color_map = {
        "": BLACK_HEX # Used as the default return value if resolution fails.
    }
    
    tree: Optional[ElementTree] = None

    # Parsing the colors.xml file into an ElementTree
    try:
        tree = parse(colors_xml_path)
    except Exception as e:
        print("[WARNING]: Unable to load the color map for the specified file.")
        print(f"[ERROR]: {e}")
        exit(1)
        
    root = tree.getroot()
    
    # Iterating through the resolved color elements within colors.xml
    for color in root.findall('color'):
        color_map[color.get('name')] = color.text

    return color_map



def load_string_map_xml(string_xml_path: str) -> Dict[str, str]:
    """Parses strings.xml into a Dict[str, str] or exits on an exception."""
    string_map = {}
    
    tree: Optional[ElementTree] = None

    # Parsing the strings.xml file into an ElementTree
    try:
        tree = parse(string_xml_path)
    except Exception as e:
        print("[WARNING]: Unable to load the string map for the specified file.")
        print(f"[ERROR]: {e}")
        exit(1)
        
    root = tree.getroot()
    
    # Iterating through the resolved values within strings.xml
    for string in root.findall('string'):
        string_map[string.get('name')] = string.text

    return string_map






#################### Resource Resolution ####################


def resolve_color_reference(color_reference_key: str) -> str:
    """
    Takes a resolved color resource from colors.xml as input.

    If the referenced string is already in hex:
        - The current value is returned without modifications.

    If the referenced string is a color reference:
        - It starts with either "@android:color/" or "@color/" (if user-defined) 
        - A lookup is performed on this key using COLOR_RESOURCES_MAP

    """
    result: Optional[str] = None

    # Removing the SDK prefix then returning the built-in color's equivalent Hex Code.
    if color_reference_key.startswith(SDK_COLOR_PREFIX):
        color_reference_key = color_reference_key.removeprefix(SDK_COLOR_PREFIX)
        result = (GRAPHICS_COLOR_MAP or {}).get(color_reference_key)
    
    # Removing the color resource prefix then returning the user-defined Hex Code representation.
    elif color_reference_key.startswith(USER_MADE_COLOR_PREFIX):
        color_reference_key = color_reference_key.removeprefix(USER_MADE_COLOR_PREFIX)
        result = (COLOR_RESOURCES_MAP or {}).get(color_reference_key)

    # Warning the user the resolution failed and ADAS will fallback to BLACK_HEX (#000000)
    if not result:
        print(f"[WARNING]: Could not locate the specified key '{color_reference_key}'.")
        print(f"[INFO]: Falling back to '{BLACK_HEX}'")
        return BLACK_HEX

    

    # Ensuring the resolved resource value is a valid hex sequence.
    # If the value is valid, it is returned, otherwise, BLACK_HEX is returned.
    return result if fc_is_already_hex(result) else BLACK_HEX


def resolve_string_reference(string_reference_key: str) -> str:
    """
    Takes a resolved string resource from string.xml as input.

    A lookup is performed using STRING_RESOURCES_MAP.
    """

    if not string_reference_key:
        print(f"[WARNING]: An empty value was returned using the key '{string_reference_key}'.")
        print("[WARNING]: This may cause the converted SVG to be malformed.")
        return ""

    # Ensuring the resolved path data value is not a NoneType.
    # This avoids an incorrect insertion during conversion.
    return (STRING_RESOURCES_MAP or {}).get(string_reference_key, "")
    





#################### Conversion/Output Functionality ####################


def convert_alpha_hex_to_decimal_str(alpha_hex: str) -> str:
    """
    Takes a 2 character hex sequence (ie. #AA) and converts it to a decimal (float) between 0.0 and 1.0.
    """
    try:
        # Converting the base-16 string to an 32 bit integer.
        # Mapping this converted integer to a decimal scale (0.0 - 1.0).
        alpha_val = int(alpha_hex, 16) / 255.0
        return str(round(alpha_val, 3))
    except ValueError:
        print(f"[WARNING]: Could not convert alpha channel '{alpha_hex}'.")
        print("[INFO]: Falling back to default value of '1.0'.")
        return "1.0"


def remove_units_from_numeric_string(numeric_string: str):
    """
    Sanitizing numeric strings, namely the height and width properties that usually contain units.
    While modern browsers will usually default to pixels when faced with an unsupported unit, this ensures broad compatibility.
    """
    
    return (numeric_string
        .replace("dp", "")
        .replace("px", "")
        .replace("dip", "")
    )


def parse_nodes_from_xml_paths(paths: List[Dict[str, str]]) -> List[str]:
    """
    Parses each path node from the provided list of paths. 
    """
    path_elements = []
    
    for path_node in paths:
        raw_fill_color: str = path_node.get("fillColor") or BLACK_HEX
        final_path_data: str = path_node.get("pathData") or ""
        final_fill_type: str = path_node.get("fillType") or ""
        
        # Handling color references via string resolution.
        if fc_has_color_reference(raw_fill_color):
            raw_fill_color = resolve_color_reference(raw_fill_color)

        # Handling string references via string resolution.
        if pd_has_string_reference(final_path_data):
            string_reference_key = final_path_data.removeprefix("@string/")
            final_path_data = resolve_string_reference(string_reference_key)
        
        # Performing a conditional expansion of the raw fill color, if required.
        raw_fill_color = expand_fc_if_needed(raw_fill_color)

        # If the raw color contains 8 hex digits, its alpha channel is removed and returned separately.
        (sanitized_fill_color, alpha_str) = split_fc_if_needed(raw_fill_color)

        # Conditionally appending either the unmodified fill color or the sanitized 6 digit hex sequence.
        final_fill_color = raw_fill_color if alpha_str is None else sanitized_fill_color
        
        # Building and appending each path element at the end of the current iteration.
        path_element = '<path fill="' + final_fill_color + '"'

        # Conditionally appending fill-opacity if the alpha channel has successfully been separated.
        if alpha_str:
            path_element += ' fill-opacity="' + alpha_str + '"'
        
        # Conditionally appending the result from the conversion "fillColor=" to "fill-rule=", if present.
        # Unlike the other optional arguments, the value for the SVG fill-rule attribute must be all lowercase.
        # Per: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Attribute/fill-rule
        if final_fill_type:
            path_element += ' fill-rule="' + final_fill_type.lower() + '"'


        # Conditionally appending the conversion result from "strokeColor=" to "stroke-color=", if present.
        path_element += resolve_and_format_stroke_color(path_node)

        # Conditionally appending the conversion result from "strokeWidth=" to "stroke-width=", if present.
        path_element += format_stroke_width(path_node)

        # An SVG is nothing if not for path data, so this is an expected value.
        path_element += ' d="' + final_path_data + '"/>'
        
        # Appending the concatenated element and continuing with the current iterator.
        path_elements.append(path_element)
    
    return path_elements


def write_output_svg(metadata_attributes: Dict[str, str], paths: List[Dict[str, str]]):
    """
    Used in convert_drawable_to_svg() to output the contents of the converted SVG.
    """
    
    # This list holds all <path> elements that were parsed from the input XML.
    path_elements: List[str] = parse_nodes_from_xml_paths(paths)
    
    # This could included in svg_contents directly, but for maintainability, it is declared as a standalone variable.
    path_data: str = "\n".join(path_elements)

    # Sanitizing the SVG height/width, alongside the viewbox height/width to ensure broad compatibility with older browsers.
    height: str = remove_units_from_numeric_string(
        metadata_attributes.get('height', '0')
    )
    width: str = remove_units_from_numeric_string(
        metadata_attributes.get('width', '0')
    )
    viewport_width: str = remove_units_from_numeric_string(
        metadata_attributes.get('viewportWidth', '0')
    )
    viewport_height: str = remove_units_from_numeric_string(
        metadata_attributes.get('viewportHeight', '0')
    )

    view_box: str = f"0 0 {viewport_width} {viewport_height}"

    svg_content: str = f'''
    <svg xmlns="{SVG_NAMESPACE}" height="{height}" width="{width}" viewBox="{view_box}">
        {path_data}
    </svg>'''.replace("    ", "")

    try:
        with open(OUTPUT_SVG_FILEPATH, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"[SUCCESS]: Converted {DRAWABLE_XML_FILEPATH} to: {OUTPUT_SVG_FILEPATH}")
    except Exception as e:
        print(f"[WARNING]: Unable to export: {OUTPUT_SVG_FILEPATH}")
        print(f"[ERROR]: {e}")


def convert_drawable_to_svg():
    """Handles the conversion operations from XML to SVG."""
    if USING_COLOR_RESOURCES:
        set_color_resource_map()

    if USING_STRING_RESOURCES:
        set_string_resource_map()

    drawable_vector_contents: Optional[str] = load_drawable_vector_xml(DRAWABLE_XML_FILEPATH)

    if drawable_vector_contents is None:
        exit(1)

    check_drawable_vector_format(drawable_vector_contents)
    
    try:
        xml_root = fromstring(drawable_vector_contents)
    except ParseError as e:
        print("[ERROR]: Unable to parse the specified file's contents using ElementTree.")
        print("[INFO]: If this issue persists with an official AOSP vector, please make a bug report using the url below.")
        print("[LINK]: https://github.com/Static-Codes/AndroidDrawableToSVG/issues")
        print(f"[ERROR]: {e}")
        exit(1)

    
    # These metadata attributes are to be expected in a properly formatted, AOSP-licensed DrawableVector. 
    metadata_attributes = {
        "height": xml_root.get(f"{ANDROID_NAMESPACE}height", ""),
        "width": xml_root.get(f"{ANDROID_NAMESPACE}width", ""),
        "viewportHeight": xml_root.get(f"{ANDROID_NAMESPACE}viewportHeight", ""),
        "viewportWidth": xml_root.get(f"{ANDROID_NAMESPACE}viewportWidth", "")
    }

    # This will be populated assuming root.findall() locates <path> elements within the XML root namespace.
    nodes = []
    
    # Iterating through each of the path nodes in the DrawableVector XML's root namespace.
    # In hindsight it was very much a mistake to use Regex for this initially.
    for node in xml_root.findall(".//path"):
        nodes.append({
            "fillColor": node.get(f"{ANDROID_NAMESPACE}fillColor", ""),
            "fillType": node.get(f"{ANDROID_NAMESPACE}fillType", ""),
            "strokeColor": node.get(f"{ANDROID_NAMESPACE}strokeColor", ""),
            "strokeWidth": node.get(f"{ANDROID_NAMESPACE}strokeWidth", ""),
            "pathData": node.get(f"{ANDROID_NAMESPACE}pathData", "")
        })

    # Informing the end-user of a non-fatal error, mostly for debugging purposes.
    if not nodes:
        print(f"[WARNING]: No <path> elements were found in {DRAWABLE_XML_FILEPATH}.")
        print("[WARNING]: This will likely impact the quality of the converted SVG.")

    # Finally, the output operation is complete (assuming this doesnt raise an exception.)
    write_output_svg(metadata_attributes, nodes)






#################### Entry Functions ####################

def usage():
    print("AndroidDrawableToSVG - A pure python utility to convert an AOSP released DrawableVector to an SVG!\n")
    
    print("Usage: adas.py [OPTIONS] \n")
    print("OPTIONS:\n")
    
    print(
        "1.    [ -h | --help ]\n"
        "\tDisplays this message.\n"
    )

    print(
        "2.    [ -d path/to/drawable.xml | --drawable=path/to/drawable.xml ]\n"
        "\tSpecifies the drawable you wish to convert to an SVG.\n"
    )

    print(
        "3.    [ -o path/to/output.svg | --output=path/to/output.svg ]\n"
        "\tSpecifies the filename to be used for the converted SVG.\n"
    )

    print(
        "4.    [ -s path/to/strings.xml | --strings=path/to/strings.xml | --strings=path1;path2;path3 ]"
        "\tSpecifies the filename(s) to be used for user-defined values."
    )

    print(
        "5.    [ -c path/to/colors.xml | --colors=path/to/colors.xml | --colors=path1;path2;path3 ]"
        "\tSpecifies the filename(s) to be used for user-defined values."
    )

    print(
        "6.    [ -v <version> | --version=<version> ]\n"
        "\tPrints the current version of ADAS.\n"
    )


def set_args(argv: List[str]):
    try:
        opts, _ = getopt(
            argv[1:], 
            "d:o:c:s:vh", 
            ["drawable=", "output=", "colors=", "strings=", "version", "help"]
        )
        
    except GetoptError:
        usage()
        exit(2)

    for opt, arg in opts:
        
        # Handles both "adas.py -h" and "adas.py --help"
        if opt == "-h" or opt == "--help":
            usage()
            exit(1)

        # Handles both "-d <drawable.xml>" and "--drawable=<drawable.xml>"
        elif opt == "-d" or opt == "--drawable":
            global DRAWABLE_XML_FILEPATH
            DRAWABLE_XML_FILEPATH = path.expanduser(arg)
            print("Starting conversion using: {}".format(DRAWABLE_XML_FILEPATH))
        
        # Handles both "-o <output.svg>" and "--output=<output.svg>"
        elif opt == "-o" or opt == "--output":
            global OUTPUT_SVG_FILEPATH
            OUTPUT_SVG_FILEPATH = path.expanduser(arg)

        # Handles:
        # "-c <colors.xml>"
        # "-c <colors1.xml:colors2.xml:colors3.xml>"
        # "--colors=<colors.xml>"
        # "--colors=<colors1.xml:colors2.xml:colors3.xml>"
        elif opt == "-c" or opt == "--colors":
            global COLORS_XML_FILEPATH
            COLORS_XML_FILEPATH = path.expanduser(arg)
            
            global USING_COLOR_RESOURCES
            USING_COLOR_RESOURCES = True

        # Handles:
        # "-s <strings.xml>"
        # "-s <strings1.xml:strings2.xml:strings3.xml>"
        # "--strings=<strings.xml>"
        # "--strings=<strings1.xml:strings2.xml:strings3.xml>"
        elif opt == "-s" or opt == "--strings":
            global STRINGS_XML_FILEPATH

            STRINGS_XML_FILEPATH = path.expanduser(arg)
            
            global USING_STRING_RESOURCES
            USING_STRING_RESOURCES = True

        # Handles both "adas.py -v" and "adas.py --version"
        elif opt == "-v" or opt == "--version":
            print(SCRIPT_VERSION)
            exit(1)


def main(argv: List[str]):
    global DRAWABLE_XML_FILEPATH
    global OUTPUT_SVG_FILEPATH
    
    set_args(argv)
    
    # Update this in the future to use argparse
    required_args = {
        "DRAWABLE": (DRAWABLE_XML_FILEPATH, "-d", "--drawable", "path to the drawable you wish to use"),
        "OUTPUT": (OUTPUT_SVG_FILEPATH, "-o", "--output", "output path for your converted SVG")
    }

    for name, (value, short_flag, long_flag, description) in required_args.items():
        if value is None:
            print(f"Error: Please specify the {description}.")
            print(f"This can be done using the {short_flag} <{name.lower()}> or {long_flag} <{name.lower()}> flag.")
            print("For more information, please use:\n\tadas.py -h")
            exit(1)

    convert_drawable_to_svg()


if __name__ == "__main__":
    main(sys.argv)