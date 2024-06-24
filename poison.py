from collections import defaultdict
import dis
from importlib.util import find_spec
import inspect
from pathlib import Path
import sys
import token
import tokenize
from types import CodeType


__MODULE__ = (p := Path(__file__)).name.removesuffix(p.suffix)

_BUILTIN_FOLDER = str(Path(sys.executable).parent.joinpath('Lib'))


ignored_contexts = {
	__file__, 
	'<frozen importlib._bootstrap>', 
	'<frozen importlib._bootstrap_external>'
}

marked_import_sources = {
	'frozen',
	'built-in'
}


def get_bytecode(file_path: str) -> dis.Bytecode:
	with open(file_path) as source_file:
		source_code = source_file.read()
	return dis.Bytecode(source_code)


def get_import_names(
		bytecode: dis.Bytecode,
		import_names: defaultdict = None,
		visited_codes: set = None
) -> defaultdict:
	if import_names is None:
		import_names = defaultdict(set)
	if visited_codes is None:
		visited_codes = set()

	for instr in bytecode:
		argval = instr.argval
		if instr.opname == 'IMPORT_NAME':
			import_names[argval].add(instr.positions.lineno)
		elif isinstance(argval, CodeType) and argval not in visited_codes:
			visited_codes.add(argval)
			nested_imports_names = get_import_names(
				bytecode=dis.Bytecode(argval), import_names=import_names, visited_codes=visited_codes
			)
			for import_name, line_numbers in nested_imports_names.items():
				import_names[import_name].update(line_numbers)
	return import_names


def filter_import_names(import_names: defaultdict, start_line: int = 0) -> set:
	if __MODULE__ in import_names:
		del import_names[__MODULE__]
	for import_name, line_numbers in import_names.items():
		filtered_line_numbers = {ln for ln in line_numbers if ln > start_line}
		import_names[import_name] = filtered_line_numbers

	return {import_name for import_name, line_numbers in import_names.items() if line_numbers}


def get_import_source_path(import_name: str) -> str | None:
	spec = find_spec(import_name)
	if spec is None:
		return
	return spec.origin


def check_import_path(import_path: str) -> bool:
	if import_path in marked_import_sources:
		return False
	marked_import_sources.add(import_path)
	return True


def get_poison_context(filename: str = None):
	if filename:
		return filename, 0
	for frame in inspect.stack():
		filename = frame.filename
		if filename not in ignored_contexts:
			return filename, frame.positions.lineno


def poison(*names: list[str], filename: str = None, recursive: bool = True):
	poisoned_file, start_line = get_poison_context(filename=filename)
	poisoned_names = set(names)
	with tokenize.open(poisoned_file) as f:
		tokens = tokenize.generate_tokens(f.readline)
		for _ in range(start_line):
			next(f)
		for t in tokens:
			if t.type == token.NAME and t.string in poisoned_names:
				raise RuntimeError(
					f'Poisoned name "{t.string}" found on line {start_line + t.start[0]}!'
				)

	print(f'{poisoned_file} is clean')
	marked_import_sources.add(poisoned_file)
	if recursive:
		file_bytecode = get_bytecode(poisoned_file)
		imports = get_import_names(bytecode=file_bytecode)
		filtered_imports = filter_import_names(import_names=imports, start_line=start_line)

		print(f'Checking imports: {filtered_imports}')
		for import_name in filtered_imports:
			import_path = get_import_source_path(import_name)
			print(f'{import_path = }')
			if import_path is None:
				continue
			if check_import_path(import_path=import_path):
				poison(*poisoned_names, filename=import_path, recursive=True)


if __name__ == '__main__':
	raise RuntimeError(f'"{__MODULE__}" module must be imported in an other file.')
