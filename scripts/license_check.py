# Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

import pathlib
from textwrap import dedent

working_dir = pathlib.Path(__file__).parent.parent.absolute()
license_short_text = dedent(
    """
    # Copyright: (c) 2024, Rafał Safin <rafal.safin@rafsaf.pl>
    # GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
    """
)


def find_python_files(path: pathlib.Path) -> list[pathlib.Path]:
    python_file_lst: list[pathlib.Path] = []
    for path, dirs, files in path.walk():
        for file in files:
            if file.endswith(".py"):
                python_file_lst.append(path / file)
        for dir in dirs:
            python_file_lst += find_python_files(path / dir)
    return python_file_lst


for python_file in find_python_files(working_dir):
    if license_short_text.strip() in python_file.read_text():
        continue
    print(f"---> {python_file}")
    current_file_text = python_file.read_text()
    with open(python_file, "w") as file_to_update:
        file_to_update.write(license_short_text.strip() + "\n\n" + current_file_text)
