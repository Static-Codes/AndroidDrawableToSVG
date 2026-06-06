#################### Disabling Byte Code Generation ####################
import sys
sys.dont_write_bytecode = True






#################### Application Imports ####################
from getopt import getopt, GetoptError
from os import path
from re import compile, DOTALL, Pattern, RegexFlag, search, VERBOSE
from typing import List, Dict, Optional
from xml.etree import ElementTree
from xml.etree.ElementTree import parse, ParseError, fromstring






#################### Constants #################### 

# The current release of ADAS (as it stands, this is a pre-release).
SCRIPT_VERSION: str = "v0.0.1-pre-release"

# Used for re.search
FLAGS: RegexFlag = VERBOSE | DOTALL

# The default/fallback value for fillColor="X" if it cannot be parsed/converted.
BLACK_HEX = "#000000"

# The root namespace for the converted SVG file.
XML_NAMESPACE = "http://www.w3.org/2000/svg"






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
COLOR_RESOURCES_MAP: Dict[str, str] = []

# The map will be populated using STRINGS_XML_FILEPATH if USING_STRING_RESOURCES is set to True.
STRING_RESOURCES_MAP: Dict[str, str] = []






################### Input Mutatation Functions ###################

def set_color_resource_map() -> None:
    global COLOR_RESOURCES_MAP
    try:
        COLOR_RESOURCES_MAP = load_color_map_xml(COLORS_XML_FILEPATH)
    except Exception as e:
        print("[WARNING]: A fatal error occured while loading COLORS_XML_FILEPATH.")
        print(f"[ERROR]: {e}")
        exit(1)


def set_string_resource_map() -> None:
    global STRING_RESOURCES_MAP
    try:
        STRING_RESOURCES_MAP = load_string_map_xml(STRINGS_XML_FILEPATH)
    except Exception as e:
        print("[WARNING]: A fatal error occured while loading STRING_RESOURCES_MAP.")
        print(f"[ERROR]: {e}")
        exit(1)






#################### Formatting Helper Functions ####################   

# If a fill_color is only 3 or 4 characters, it is missing one of each R, G, B, and potentially A (Alpha).
# An expanded fill_color will be returned if the length is 3 or 4, otherwise, the original value is returned.
def expand_fc_if_needed(fill_color: str) -> str:
    if not fill_color.startswith("#"): 
        return hex_str
    
    # Handling all other strings that start with a hashtag, but are not 4 or 4 chars in length
    if not len(fill_color) in [4, 5]:
        return hex_str

    # Expanding #RGB to #RRGGBB
    if len(fill_color) == 4:
        return "#" + "".join([char*2 for char in fill_color[1:]])

    # Expanding #RGBA to #RRGGBBAA
    if len(fill_color) == 5:
        return "#" + "".join([char*2 for char in fill_color[1:]])


# Checks if the current fill color is a color reference, if so, additional resolution is required.
def fc_has_color_reference(fill_color: str) -> bool:
    if not isinstance(fill_color, str):
        return False

    return False if not fill_color else "@color/" in fill_color


# Checking if a hex sequence is valid PRIOR to any conversion attempts, ultimately to save cpu cycles.
def fc_is_already_hex(fill_color: str) -> bool:

    color_length = len(fill_color)

    # Ensures the fill color has the correct formatting (#RRBBGG) or (#RRBBGGAA).
    if not (fill_color.startswith("#") and (color_length in [7, 9])):
        return False
    
    # Ensuring the hex sequence can be successfully converted to a base-16 integer.
    # This handles individual character validation from 0-9 and A-Z respectively.
    # Finally, the hex sequence to compared against the max value for each to ensure a valid color is present.
    try:
        hex_as_int_repr = int(fill_color[1:], base=16)

        # Handling the max value for both #RRGGBB and #RRBBGGAA
        max_int_value = 0xFFFFFF if color_length == 7 else 0xFFFFFFFF

        return hex_as_int_repr <= max_int_value 

    except Exception as e: # Silently returning as this in a non-fatal exception.
        print(f"[INFO]: Hex conversion required for fill color '{fill_color}'")
        return False


# Checking if the provided contents contains the Android Open Source Project (AOSP)'s Copyright.
def has_aosp_copyright(contents: str) -> bool:

    PATTERN = r"Copyright\s+\(C\)\s+\d{4}.*?The\s+Android\s+Open\s+Source\s+Project"

    REGEX = compile(PATTERN, FLAGS)
    
    return REGEX.search(contents) is not None


# Checking if the provided contents contains the expected XML header attribute.   
def has_xml_header(contents: str) -> bool:
    return contents.startswith('<?xml version="1.0" encoding="utf-8"?>')


# Checks if the current path data is a string reference, if so, additional resolution is required.
def pd_has_string_reference(path_data: str) -> bool:
    if not isinstance(path_data, str):
        return False

    return False if not path_data else "@string/" in path_data


# Both of the checks below are non-fatal and serve primarily for debugging purposes.
#
# It is entirely possible to parse a raw <vector>...</vector> however:
#
# The AOSP releases standardized DrawableVectors here:
# https://cs.android.com/androidx/platform/frameworks/support/+/androidx-main:vectordrawable/vectordrawable/src/androidTest/res/

def check_drawable_vector_format(drawable_vector_contents: str):
    
    if not has_xml_header(drawable_vector_contents):
        print(f"[WARNING]: The XML header is missing for: {DRAWABLE_XML_FILEPATH}")
        print("[WARNING]: This may impact the result of the current conversion.")
        print("[INFO]: Attempting to continue..")
    
    if not has_aosp_copyright(drawable_vector_contents):
        print(f"[WARNING]: The Android Open Source Project (AOSP) copyright was not located.")
        print("[WARNING]: This may impact the result of the current conversion.")
        print("[INFO]: Attempting to continue..")






#################### File Parsing Functionality ####################

def get_drawable_xml_pattern() -> Pattern:
    
    VECTOR_HEADER = r"""
        <vector\s+
            xmlns:android="http://schemas\.android\.com/apk/res/android"
            \s+android:height="(?P<height>.*)"
            \s+android:width="(?P<width>.*)"
            \s+android:viewportHeight="(?P<viewportHeight>.*)"
            \s+android:viewportWidth="(?P<viewportWidth>.*)"
        >
    """

    PATH_BODY = r"""
        \s*<path
            \s+android:fillColor="@color/(?P<fillColor>.*)"
            \s+android:strokeColor="@color/(?P<strokeColor>.*)"
            \s+android:strokeWidth="(?P<strokeWidth>.*)"
            \s+android:pathData="(?P<pathData>.*)"
        />
    """

    VECTOR_CLOSING_TAG = r"\s*</vector>"

    PATTERN = VECTOR_HEADER + PATH_BODY + VECTOR_CLOSING_TAG

    return compile(PATTERN, FLAGS)

    # Left to allow for easier debugging on regex101.com
    # return compile("<vector xmlns:android=\"http://schemas\.android\.com/apk/res/android\"\n\s{1,}android:height=\"(?P<height>.*)\"\n\s{1,}android:width=\"(?P<width>.*)\"\n\s{1,}android:viewportHeight=\"(?P<viewportHeight>.*)\"\n\s{1,}android:viewportWidth=\"(?P<viewportWidtht>.*)\">\n{1,}\s{1,}<path\n\s{1,}android:fillColor=\"@color/(?P<fillColor>.*)\"\n\s{1,}android:strokeColor=\"@color/(?P<strokeColor>.*)\"\n\s{1,}android:strokeWidth=\"(?P<strokeWidth>.*)\"\n\s{1,}android:pathData=\"(?P<pathData>.*)\"/>\n{1,}</vector>")

# Parses the DrawableVector XML and returns its contents as a string, or exits on an exception.
def load_drawable_vector_xml(drawable_vector_path: str) -> str:
    try:
        with open(drawable_vector_path, "r", encoding="utf-8") as file:
            return file.read()
    
    except Exception as e:
        print("An exception occured while trying to read the provided XML file.")
        print(f"Error: {e}")
        exit(1)


# Parses colors.xml into a Dict[str, str] or exits on an exception.
def load_color_map_xml(colors_xml_path: str) -> Dict[str, str]:
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


# Parses strings.xml into a Dict[str, str] or exits on an exception.
def load_string_map_xml(string_xml_path: str) -> Dict[str, str]:
    string_map = {}
    
    tree: Optional[ElementTree] = None

    # Parsing the strings.xml file into an ElementTree
    try:
        tree = parse(string_xml_path)
    except Exception as e:
        print("[WARNING]: Unable to load the color map for the specified file.")
        print(f"[ERROR]: {e}")
        exit(1)
        
    root = tree.getroot()
    
    # Iterating through the resolved values within strings.xml
    for string in root.findall('string'):
        string_map[string.get('name')] = string.text

    return string_map






#################### Resource Resolution ####################

# Takes a resolved color resource from colors.xml as input.
#
# If the referenced string is already in hex:
#   - The current value is returned without modifications.
#
# If the referenced string is a color reference (starts with "@color/") 
#   - A lookup is performed using the color map from COLOR_RESOURCES_MAP

def resolve_color_reference(color_reference_key: str) -> str:

    result = (COLOR_RESOURCES_MAP or {}).get(color_reference_key)

    if not result:
        print(f"[WARNING]: Could not locate the specified key '{color_reference_key}'.")
        print(f"[INFO]: Falling back to '{BLACK_HEX}'")
        return BLACK_HEX

    


    # Ensuring the resolved resource value is a valid hex sequence.
    # If the value is valid, it is returned, otherwise, BLACK_HEX is returned.
    return result if fc_is_already_hex(result) else BLACK_HEX


# Takes a resolved string resource from string.xml as input.
#
# A lookup is performed using the string map from STRING_RESOURCES_MAP.

def resolve_string_reference(string_reference_key: str) -> str:
    if not string_reference_key:
        print(f"[WARNING]: An empty value was returned using the key '{string_reference_key}'.")
        print(f"[WARNING]: This may cause the converted SVG to be malformed.")
        return ""

    # Ensuring the resolved path data value is not a NoneType.
    # This avoids an incorrect insertion during conversion.
    return (STRING_RESOURCES_MAP or {}).get(string_reference_key, "")
    





#################### Conversion/Output Functionality ####################

# Used in convert_drawable_to_svg() to output the contents of the converted SVG.
def write_output_svg(generic_attributes: Dict[str, str], paths: List[Dict[str, str]]):
    
    path_elements = []

    for path in paths:
        original_fill_color: Optional[str] = path.get("fillColor") or BLACK_HEX
        original_path_data: Optional[str] = path.get("pathData") or ""

        final_fill_color: str = original_fill_color
        final_path_data: str = original_path_data

        if fc_has_color_reference(original_fill_color):
            color_reference_key = original_fill_color.removeprefix("@color/")
            final_fill_color = resolve_color_reference(color_reference_key)

        if pd_has_string_reference(original_path_data):
            string_reference_key = original_path_data.removeprefix("@string/")
            final_path_data = resolve_string_reference(string_reference_key)
        
        # Performing a conditional expansion of the final color, if required.
        final_fill_color = expand_fc_if_needed(final_fill_color)
        
        # Ensuring that if stroke color or stroke width are missing, the conversion is not impacted.
        stroke_color = f' stroke="{path.get("strokeColor")}"' if path.get("strokeColor") else ""
        stroke_width = f' stroke-width="{path.get("strokeWidth")}"' if path.get("strokeWidth") else ""
        
        # Building and appending each path element at the end of the current iteration.
        # This needs to be rewritten to handle "fillType="
        path_element = f'<path fill="{final_fill_color}"{stroke_color}{stroke_width} d="{final_path_data}"/>'
        path_elements.append(path_element)
    
    # This could included in svg_contents directly, but for maintainability, it is declared as a standalone variable.
    path_data = "\n\t\t".join(path_elements)

    # Accessing the generic attributes directly is expected to be safe, as they are required for a valid input file.
    # TODO: Fix the formatting of this for my OCD sake.
    svg_content = f'''
<svg 
    xmlns="{XML_NAMESPACE}"
    height="{generic_attributes.get('height')}" 
    width="{generic_attributes.get('width')}" 
    viewBox="0 0 {generic_attributes.get('viewportWidth')} {generic_attributes.get('viewportHeight')}">
        {path_data}
</svg>'''

    try:
        with open(OUTPUT_SVG_FILEPATH, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"[SUCCESS]: Converted {DRAWABLE_XML_FILEPATH} to: {OUTPUT_SVG_FILEPATH}")
    except Exception as e:
        print(f"[WARNING]: Unable to export: {OUTPUT_SVG_FILEPATH}")
        print(f"[ERROR]: {e}")


# Handles the conversion operations from XML to SVG.
def convert_drawable_to_svg():
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

    android_namespace = "{http://schemas.android.com/apk/res/android}"

    # These attributes are to be expected in a properly formatted, AOSP-licensed DrawableVector. 
    generic_attributes = {
        "height": xml_root.get(f"{android_namespace}height", ""),
        "width": xml_root.get(f"{android_namespace}width", ""),
        "viewportHeight": xml_root.get(f"{android_namespace}viewportHeight", ""),
        "viewportWidth": xml_root.get(f"{android_namespace}viewportWidth", "")
    }

    # This will be populated assuming root.findall() locates <path> elements within the XML root namespace.
    nodes = []
    
    # Iterating through each of the path nodes in the DrawableVector XML's root namespace.
    # In hindsight it was very much a mistake to use Regex for this initially.
    # TODO: Add fillType support through string resolution.
    for node in xml_root.findall(".//path"):
        nodes.append({
            "fillColor": node.get(f"{android_namespace}fillColor", ""),
            "strokeColor": node.get(f"{android_namespace}strokeColor", ""),
            "strokeWidth": node.get(f"{android_namespace}strokeWidth", ""),
            "pathData": node.get(f"{android_namespace}pathData", "")
        })

    if not nodes:
        print(f"[WARNING]: No <path> elements were found in {DRAWABLE_XML_FILEPATH}.")
        print("[WARNING]: This will likely impact the quality of the converted SVG.")

    write_output_svg(generic_attributes, nodes)




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
        "2.    [ -d <drawable.xml> | --drawable=<drawable> ]\n"
        "\tSpecifies the drawable you wish to convert to an SVG.\n"
    )

    print(
        "3.    [ -o <output.svg> | --output=<output.svg> ]\n"
        "\tSpecifies the filename to be used for the converted SVG.\n"
    )

    print(
        "8.    [ -v <version> | --version=<version> ]\n"
        "\tBy default auto2cmake pins minimum version support to CMake 2.8+\n"
        "\tBy passing this flag, auto2cmake will use the specified version.\n"
    )


def set_args(argv: List[str]):
    try:
        opts, _ = getopt(
            argv[1:], 
            "d:o:c:s:v:h", 
            ["drawable=", "output=", "colors=", "strings=", "version=", "help"]
        )
        
    except GetoptError:
        usage()
        exit(2)

    for opt, arg in opts:
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

        # Handles both "-c <colors.xml>" and "--colors=<colors.xml>"
        elif opt == "-c" or opt == "--colors":
            global COLORS_XML_FILEPATH
            COLORS_XML_FILEPATH = path.expanduser(arg)
            
            global USING_COLOR_RESOURCES
            USING_COLOR_RESOURCES = True

        # Handles both "-s <strings.xml>" and "--strings=<strings.xml>"
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