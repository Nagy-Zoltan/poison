import inspect
import os
import token
import tokenize


__MODULE__ = __file__.split(os.sep)[-1].split('.')[0]


ignored_filenames = {
	__file__, 
	'<frozen importlib._bootstrap>', 
	'<frozen importlib._bootstrap_external>'
}


def poison(*names):
	poisoned_names = set(names)
	for frame in inspect.stack():
		filename = frame.filename
		if filename not in ignored_filenames:
			poisoned_file = filename
			start_line = frame.positions.lineno
			break
	else:
		raise RuntimeError(f'"{__MODULE__}" module must be imported in an other file.')

	with tokenize.open(poisoned_file) as f:
		tokens = tokenize.generate_tokens(f.readline)
		for _ in range(start_line):
			next(tokens)
		for t in tokens:
			if t.type == token.NAME and t.string in poisoned_names:
				raise RuntimeError(
					f'Poisoned name "{t.string}" found on line {t.start[0]}!'
				)


if __name__ == '__main__':
	raise RuntimeError(f'"{__MODULE__}" module must be imported in an other file.')
