# AndroidDrawableToSVG

AndroidDrawableToSVG **(ADAS)** is a simple and lightweight utility to convert an Android DrawableVector to a universal SVG.


## Requirements
ADAS only requires Python 3.9+, no additional packages or dependencies are needed!


## Simple Usage:

Once you've cloned the repository, you can test **ADAS** by executing:
#### Windows

```bash
python adas.py -d example.xml -o example.svg
```

#### Linux/MacOS

```bash
python3 adas.py -d example.xml -o example.svg
```


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
| `-d`, `--drawable=<path/to/drawable.xml>` | Defines the drawable you wish to convert. | **Yes** |
| `-o`, `--output=<path/to/output.svg>` | Defines the filename/filepath to used for the converted SVG. | **Yes** |
| `-c`, `--colors=<path/to/colors.xml>` | Defines the filepath to used for resolving color references. | **No** |
| `-s`, `--strings=<path/to/strings.xml>` | Defines the filepath to used for resolving string references. | **No** |
| `-v`, `--version=<version>` | Prints the current version of ADAS. | No |



## TODO
- Add support for complex DrawableVectors that require multiple `colors.xml` and `strings.xml` files.
- Add support for `?attr`.
- Replace `getopt` with `argparse`.