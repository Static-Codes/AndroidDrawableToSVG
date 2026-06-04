# AndroidDrawableToSVG

AndroidDrawableToSVG **(ADAS)** is a simple utility to convert an Android DrawableVector to a universal SVG.


## Requirements
ADAS only requires Python 3.X, no additional packages or dependencies are needed!


## Usage:
ADAS is both lightweight and user-friendly!

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
| `-d`, `--drawable=<path/to/drawable.xml>` | Defines the drawable you wish to convert. | **Yes** |
| `-o`, `--output=<path/to/output.svg>` | Defines the filename to used for the converted SVG. | **Yes** |
| `-v`, `--version=<version>` | Prints the version of ADAS. | No |


## Try it yourself

Once you've cloned the repository, you can test **ADAS** by executing:
#### Windows

```bash
python adas.py -d example.xml -o example.svg
```

#### Linux/MacOS

```bash
python3 adas.py -d example.xml -o example.svg
```

## TODO
- Add color mapping (map `@color/X` to `#hex`)
- Replace `getopt` with `argparse`