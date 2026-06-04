import sys
sys.dont_write_bytecode = True

from getopt import getopt, GetoptError
from os import path
from re import compile, DOTALL, Pattern, RegexFlag, search, VERBOSE
from typing import List, Dict, Optional


SCRIPT_VERSION: str = "v0.0.1"
FLAGS: RegexFlag = VERBOSE | DOTALL
DRAWABLE_XML_FILEPATH: Optional[str] = None
OUTPUT_SVG_FILEPATH: Optional[str] = None


def read_xml_file(file_path: str) -> Optional[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    
    except Exception as e:
        print("An exception occured while trying to read the provided XML file.")
        print(f"Error: {e}")
        return None


def generate_xml_regex() -> Pattern:
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

    FLAGS = VERBOSE | DOTALL

    return compile(PATTERN, FLAGS)

    # Left for reference for easy testing with regex101.com
    # return compile("<vector xmlns:android=\"http://schemas\.android\.com/apk/res/android\"\n\s{1,}android:height=\"(?P<height>.*)\"\n\s{1,}android:width=\"(?P<width>.*)\"\n\s{1,}android:viewportHeight=\"(?P<viewportHeight>.*)\"\n\s{1,}android:viewportWidth=\"(?P<viewportWidtht>.*)\">\n{1,}\s{1,}<path\n\s{1,}android:fillColor=\"@color/(?P<fillColor>.*)\"\n\s{1,}android:strokeColor=\"@color/(?P<strokeColor>.*)\"\n\s{1,}android:strokeWidth=\"(?P<strokeWidth>.*)\"\n\s{1,}android:pathData=\"(?P<pathData>.*)\"/>\n{1,}</vector>")
    

def has_aosp_copyright(contents) -> bool:
    PATTERN = r"Copyright\s+\(C\)\s+\d{4}.*?The\s+Android\s+Open\s+Source\s+Project"
    FLAGS = VERBOSE | DOTALL

    REGEX = compile(PATTERN, FLAGS)
    
    return REGEX.search(contents) is not None
    

def has_xml_header(contents: str) -> bool:
    return contents.startswith('<?xml version="1.0" encoding="utf-8"?>')


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
    global DRAWABLE_XML_FILEPATH
    global OUTPUT_SVG_FILEPATH

    try:
        opts, _ = getopt(
            argv[1:], 
            "d:o:v:h", 
            ["drawable=", "output=", "version=", "help"]
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
            DRAWABLE_XML_FILEPATH = path.expanduser(arg)
            print("Starting conversion using: {}".format(DRAWABLE_XML_FILEPATH))
        
        # Handles both "-o <output.svg>" and "--output=<output.svg>"
        elif opt == "-o" or opt == "--output":
            OUTPUT_SVG_FILEPATH = arg

        elif opt == "-v" or opt == "--version":
            print(SCRIPT_VERSION)
            exit(1)

def write_svg_output(groups: Dict[str, any]):
    global DRAWABLE_XML_FILEPATH
    global OUTPUT_SVG_FILEPATH
    
    # Add color mapping then
    # Replace fill="000000" with fill="{groups['fillColor']}" 
    svg_content = f'''<svg 
        xmlns="http://www.w3.org/2000/svg" 
        height="{groups['height']}" 
        width="{groups['width']}" 
        viewBox="0 0 {groups['viewportWidth']} {groups['viewportHeight']}">
        <path 
            fill="#000000" 
            stroke="{groups['strokeColor']}" 
            stroke-width="{groups['strokeWidth']}" 
            d="{groups['pathData']}"/>
    </svg>'''

    try:
        with open(OUTPUT_SVG_FILEPATH, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"[SUCCESS]: Converted {DRAWABLE_XML_FILEPATH} to: {OUTPUT_SVG_FILEPATH}")
    except Exception as e:
        print(f"[WARNING]: Unable to export: {OUTPUT_SVG_FILEPATH}")
        print(f"[ERROR]: {e}")


def do_file_conversion():
    global DRAWABLE_XML_FILEPATH

    xml_contents: Optional[str] = read_xml_file(DRAWABLE_XML_FILEPATH)

    if xml_contents is None:
        exit(1)

    if not has_xml_header(xml_contents):
        print(f"[WARNING]: The XML header is missing for: {DRAWABLE_XML_FILEPATH}")
        print("[WARNING]: This may impact the result of the current conversion.")
        print("[INFO]: Attempting to continue..")
    
    if not has_aosp_copyright(xml_contents):
        print(f"[WARNING]: The Android Open Source Project (AOSP) copyright was not located.")
        print("[WARNING]: This may impact the result of the current conversion.")
        print("[INFO]: Attempting to continue..")
    
    xml_regex: Pattern = generate_xml_regex()

    match = xml_regex.search(xml_contents)

    if not match:
        print("[ERROR]: Unable to parse the specified file's contents using regular expression.")
        print("[INFO]: If this issue persists with an official AOSP vector, please make a bug report using the url below.")
        print("[ISSUES LINK]: https://github.com/Static-Codes/AndroidDrawableToSVG/issues")
        exit(1)

    groups: Dict[str, any] = match.groupdict()

    write_svg_output(groups)





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

    do_file_conversion()


if __name__ == "__main__":
    main(sys.argv)