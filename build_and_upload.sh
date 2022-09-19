#!/bin/bash

# configure ~/.pypirc
# username: __token__
# password: actual token including api prefix
# call at root of directory where pyproject.toml file lies

python3 -m build

# upload to testpypi
python3 -m twine upload --repository testpypi dist/*