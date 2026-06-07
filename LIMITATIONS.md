# Known Limitations for ADAS

- 1. **ADAS** currently does not support `android:tint`.

- 2. **ADAS** currently does not support "Stroke Only" path data.
    - If you require this for your workflow, you will have to:
        - Manually replace the fill color for each of the transparent paths to `@android:color/transparent`.
        

- 3. **ADAS** does not currently create new subdirectories.
    - You must point the output file to an existing subdirectory, or ADAS will use the current working directory.


- 4. **ADAS** can only process the namespace `android:` using the `-d` or `--drawable` flag.
    - Other namespaces (like `app:`) will cause ADAS to throw a fatal exception.
    - To fix this, use a text editor to replace the existing namespace with `android:`

- 5. **ADAS** does not support flattening of multiple `colors.xml` and `strings.xml` files.
    - If your VectorDrawable requires this, you will have to:
        - Combine all color reference files into one large `colors.xml` file.
        - Repeat the step above for all string reference files into `strings.xml`
        - Pass the additional arguments `--colors=<path/to/colors.xml> --strings=<path/to/strings>` to `adas.py`

- 6. **ADAS** does not support `<resources>` as an XML root namespace, only the `<vector>` root namespace can be converted.

- 6. **ADAS** does not support attribute references (`?attr`).

- 7. **ADAS** does not support nested `<group>` elements, such as:
    ```xml
    <vector>
        <path d="some path data">
        <path d="some other path data">
        <group name="some name">
            <g transform="math here">
        </group>
    </vector>
    ```