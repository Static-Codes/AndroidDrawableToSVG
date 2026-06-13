# AndroidDrawableToSVG

AndroidDrawableToSVG **(ADAS)** is a simple and lightweight utility to convert an Android DrawableVector to a universal SVG.


## Requirements
ADAS only requires Python 3.9+, no additional packages or dependencies are needed!


## Quick Start Guide:

Once you've cloned the repository, you can test **ADAS** by executing:
#### Windows

```bash
python adas.py -d tests/quick_start.xml -o example.svg
```

#### Linux/MacOS

```bash
python3 adas.py -d tests/quick_start.xml -o example.svg
```

Once you have executed the above command, you should see a file called `example.svg` containing a checkmark.

## Advanced Usage:

#### Windows

```bash
python adas.py [OPTIONS]
```

#### Linux/MacOS

```bash
python3 adas.py [OPTIONS]
```

### Options
| Argument | Description | Required |
| :--- | :--- | :--- |
| `-h`, `--help` | Displays more detailed information on supported commands. | No |
| `-d path/to/drawable.xml`, `--drawable=path/to/drawable.xml` | Defines the drawable you wish to convert. | **Yes** |
| `-o path/to/output.svg`, `--output=path/to/output.svg` | Defines the filename/filepath to used for the converted SVG. | **Yes** |
| `-c path/to/colors.xml`, `--colors=path/to/colors.xml`, `--colors=path1;path2;path3` | Defines the filepath(s) to used for resolving color references. | **No** |
| `-s path/to/strings.xml`, `--strings=path/to/strings.xml`, `--strings=path1;path2;path3` | Defines the filepath(s) to used for resolving string references. | **No** |
| `-v`, `--version` | Prints the current version of ADAS. | No |


## Known Limitations/Issues
For the complete list of known limitations and issues, please see [this](LIMITATIONS.md) file.



## Future QoL Plans
- Addressing the Limitations/Issues above.
- Replacing `getopt` with `argparse` for easier maintainability.