import sys
import math

configs = {'L1 #sets': 0, 'L1 lines/set': 0, 'L1 block size': 0,
		   'L2 #sets': 0, 'L2 lines/set': 0, 'L2 block size': 0}

def parse_arguments(args):
	trace_file = ''
	for i in range(len(args)):
		if args[i] == '-L1s':
			configs['L1 #sets'] = int(math.pow(2, int(args[i + 1])))
		elif args[i] == '-L1E':
			configs['L1 lines/set'] = int(args[i + 1])
		elif args[i] == '-L1b':
			configs['L1 block size'] = int(math.pow(2, int(args[i + 1])))
		elif args[i] == '-L2s':
			configs['L2 #sets'] = int(math.pow(2, int(args[i + 1])))
		elif args[i] == '-L2E':
			configs['L2 lines/set'] = int(args[i + 1])
		elif args[i] == '-L2b':
			configs['L2 block size'] = int(math.pow(2, int(args[i + 1])))
		elif args[i] == '-t':
			trace_file = args[i + 1]
	return trace_file

def create_cache(total_sets, total_lines, block_size, cache):
	"""
	the caches are stored in the following way for better manipulation:

	{set_number:
		{line number:
			{
				v_bit: 0/1,
				tag: ...,
				block: [byte_1, ...]
			}, ...
		}, ...
	}
	"""
	for i in range(total_sets):
		cache.setdefault(str(i), {})
		for j in range(total_lines):
			cache[str(i)].setdefault(str(j), {'v_bit': 0, 'tag': '', 'block': []})
			for k in range(block_size):
				cache[str(i)][str(j)]['block'].append('')

	return cache

def parse_memory(aligned_ram):
	memory_image = ''
	with open('ram.txt') as ram:
		memory_image = ram.readlines()[0].replace(' ', '')
	
	byte_size = 8
	bits_per_hex = 4
	max_segment_size = (byte_size * configs['L1 block size']) // bits_per_hex
	index = 0
	for i in range(1, len(memory_image)):
		if i % max_segment_size == 0:
			aligned_ram.setdefault(str(index), memory_image[i-max_segment_size:i])
			index += 1

	return aligned_ram

def main():
	L1_data = {}
	L1_instruction = {}
	L2_cache = {}
	aligned_ram = {}

	args = sys.argv
	if len(args) != 15:
		print("insufficient number of arguments. exiting the program")
		return 1

	trace_file = parse_arguments(args)

	L1_data = create_cache(configs['L1 #sets'], configs['L1 lines/set'], configs['L1 block size'], L1_data)
	L1_instruction = create_cache(configs['L1 #sets'], configs['L1 lines/set'], configs['L1 block size'], L1_instruction)
	L2_cache = create_cache(configs['L2 #sets'], configs['L2 lines/set'], configs['L2 block size'], L2_cache)

	aligned_ram = parse_memory(aligned_ram)

main()
