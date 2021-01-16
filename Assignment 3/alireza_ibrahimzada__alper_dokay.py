import sys
import math

hex_binary = {'0': '0000', '1': '0001', '2': '0010', '3': '0011', '4': '0100', '5': '0101', '6': '0110', '7': '0111', 
              '8': '1000', '9': '1001', 'A': '1010', 'B': '1011', 'C': '1100', 'D': '1101', 'E': '1110', 'F': '1111'}

configs = {'L1 #sets': 0, 'L1 lines/set': 0, 'L1 block size': 0,
		   'L2 #sets': 0, 'L2 lines/set': 0, 'L2 block size': 0}

eviction_queue = {}

performance = {'L1 instruction hits': 0, 'L1 instruction misses': 0, 'L1 instruction evictions': 0,
			   'L1 data hits': 0, 'L1 data misses': 0, 'L1 data evictions': 0,
			   'L2 hits': 0, 'L2 misses': 0, 'L2 evictions': 0}

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
				time : 0,
				tag: ...,
				block: [byte_1, ...]
			}, ...
		}, ...
	}
	"""
	for i in range(total_sets):
		cache.setdefault(str(i), {})
		eviction_queue.setdefault(str(i), [])
		for j in range(total_lines):
			cache[str(i)].setdefault(str(j), {'v_bit': 0, 'tag': '', 'time': 0, 'block': []})
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

def hex_to_bin(hex_value):
	binary_number = ''
	for hex_number in hex_value:
		binary_number += hex_binary[hex_number]
	return binary_number

def bin_to_dec(binary_number):
	sum_ = 0
	for i in range(len(binary_number)):
		sum_ += int(binary_number[i]) * math.pow(2, len(binary_number) - i - 1)
	return sum_

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


	with open(trace_file) as tf:
		for line in tf:
			trace = line.replace(',', '').strip().split()
			address = trace[1]
			size = trace[2]
			if trace[0] == 'I':   # instruction load
				pass

			elif trace[0] == 'L':   # data load
				pass

			elif trace[0] == 'S':   # data store
				data = trace[3]

			elif trace[0] == 'M':   # data load and then data store
				data = trace[3]

main()
