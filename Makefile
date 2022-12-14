
all: lint_node lint_python

TARGET_DIRS:=./purepale
OUTPUT_STAT:=/dev/stdout

flake8:
	find $(TARGET_DIRS) | grep '\.py$$' | grep -v third_party | xargs flake8
black:
	find $(TARGET_DIRS) | grep '\.py$$' | grep -v third_party | xargs black --diff | diff /dev/null -
isort:
	find $(TARGET_DIRS) | grep '\.py$$' | grep -v third_party | xargs isort --diff | diff /dev/null -
pydocstyle:
	find $(TARGET_DIRS) | grep '\.py$$' | grep -v tests | grep -v third_party | xargs pydocstyle --ignore=D100,D101,D102,D103,D104,D105,D107,D203,D212
	
lint_python: flake8 black isort pydocstyle


pyright:
	npx pyright

markdownlint:
	find . -type d \( -name node_modules -o -name .venv \) -prune -o -type f -name '*.md' -print \
	| xargs npx markdownlint --config ./.markdownlint.json

lint_node:
	npm run test
