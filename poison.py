from collections import defaultdict
import dis
import inspect
import os
import token
import tokenize
from types import CodeType


__MODULE__ = __file__.split(os.sep)[-1].split('.')[0]


ignored_filenames = {
	__file__, 
	'<frozen importlib._bootstrap>', 
	'<frozen importlib._bootstrap_external>'
}


def get_bytecode(file_path: str) -> dis.Bytecode:
	with open(file_path) as source_file:
		source_code = source_file.read()
	return dis.Bytecode(source_code)


def get_imports(bytecode: dis.Bytecode, imports: defaultdict = None, visited_codes: set = None) -> defaultdict:
	if imports is None:
		imports = defaultdict(set)
	if visited_codes is None:
		visited_codes = set()

	for instr in bytecode:
		argval = instr.argval
		if instr.opname == 'IMPORT_NAME':
			imports[argval].add(instr.positions.lineno)
		elif isinstance(argval, CodeType) and argval not in visited_codes:
			visited_codes.add(argval)
			nested_imports = get_imports(bytecode=dis.Bytecode(argval), imports=imports, visited_codes=visited_codes)
			for import_name, line_numbers in nested_imports.items():
				imports[import_name].update(line_numbers)
	return imports


def filter_imports(imports: defaultdict, start_line: int = 0) -> set:
	if __MODULE__ in imports:
		del imports[__MODULE__]
	for import_name, line_numbers in imports.items():
		filtered_line_numbers = {ln for ln in line_numbers if ln > start_line}
		imports[import_name] = filtered_line_numbers

	return {import_name for import_name, line_numbers in imports.items() if line_numbers}


def get_poison_context(filename: str = None):
	if filename:
		return filename, 0
	for frame in inspect.stack():
		filename = frame.filename
		if filename not in ignored_filenames:
			return filename, frame.positions.lineno


def poison(*names: list[str], recursive: bool = True, filename: str = None):
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
	if recursive:
		file_bytecode = get_bytecode(poisoned_file)
		imports = get_imports(bytecode=file_bytecode)
		filtered_imports = filter_imports(imports=imports, start_line=start_line)

		print(f'Checking imports: {filtered_imports}')


if __name__ == '__main__':
	raise RuntimeError(f'"{__MODULE__}" module must be imported in an other file.')
