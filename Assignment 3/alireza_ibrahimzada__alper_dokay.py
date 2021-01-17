import sys
import math
import json

hex_binary = {'0': '0000', '1': '0001', '2': '0010', '3': '0011', '4': '0100', '5': '0101', '6': '0110', '7': '0111', 
              '8': '1000', '9': '1001', 'A': '1010', 'B': '1011', 'C': '1100', 'D': '1101', 'E': '1110', 'F': '1111'}

binary_hex = {'0000': '0', '0001': '1', '0010': '2', '0011': '3', '0100': '4', '0101': '5', '0110': '6', '0111': '7',
			  '1000': '8', '1001': '9', '1010': 'A', '1011': 'B', '1100': 'C', '1101': 'D', '1110': 'E', '1111': 'F'}

configs = {'L1 #sets': 0, 'L1 lines/set': 0, 'L1 block size': 0, 'L1 #setBits': 0, 'L1 #blockBits': 0,
		   'L2 #sets': 0, 'L2 lines/set': 0, 'L2 block size': 0, 'L2 #setBits': 0, 'L2 #blockBits': 0
		   }

eviction_queue = {'L1D': {}, 'L1I': {}, 'L2': {}} 

performance = {'L1I hits': 0, 'L1I misses': 0, 'L1I evictions': 0,
			   'L1D hits': 0, 'L1D misses': 0, 'L1D evictions': 0,
			   'L2 hits': 0, 'L2 misses': 0, 'L2 evictions': 0}

def parse_arguments(args):
	trace_file = ''
	for i in range(len(args)):
		if args[i] == '-L1s':
			configs['L1 #sets'] = int(math.pow(2, int(args[i + 1])))
			configs['L1 #setBits'] = int(args[i + 1])  # bits stored for substring process in each operation
		elif args[i] == '-L1E':
			configs['L1 lines/set'] = int(args[i + 1])
		elif args[i] == '-L1b':
			configs['L1 block size'] = int(math.pow(2, int(args[i + 1])))
			configs['L1 #blockBits'] = int(args[i + 1])  # bits stored for substring process in each operation
		elif args[i] == '-L2s':
			configs['L2 #sets'] = int(math.pow(2, int(args[i + 1])))
			configs['L2 #setBits'] = int(args[i + 1])  # bits stored for substring process in each operation
		elif args[i] == '-L2E':
			configs['L2 lines/set'] = int(args[i + 1])
		elif args[i] == '-L2b':
			configs['L2 block size'] = int(math.pow(2, int(args[i + 1])))
			configs['L2 #blockBits'] = int(args[i + 1])  # bits stored for substring process in each operation
		elif args[i] == '-t':
			trace_file = args[i + 1]
	return trace_file

def create_cache(total_sets, total_lines, block_size, cache, cache_name):
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
		eviction_queue[cache_name].setdefault(str(i), [])
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
		binary_number += hex_binary[hex_number.upper()]
	return binary_number

def bin_to_dec(binary_number):
	sum_ = 0
	for i in range(len(binary_number)):
		sum_ += int(binary_number[i]) * math.pow(2, len(binary_number) - i - 1)
	return str(int(sum_))

def bin_to_hex(binary_number):
	hex_number = ''
	for i in range(0, len(binary_number), 4):
		hex_number += binary_hex[binary_number[i: i + 4]]
	return hex_number

def post_normalize_tag(tag_value, tag_length):
	if len(tag_value) == tag_length:
		return tag_value

	while (tag_length % 4 != 0):
		tag_length -= 1
	
	new_tag_value = (tag_length - len(tag_value)) * '0'
	new_tag_value += tag_value

	return new_tag_value

def instruction_load(aligned_ram, address, size, L1_instruction, L2_cache, L1I_time, L2_time):
	binary_value = hex_to_bin(address)
	decimal_value = bin_to_dec(binary_value)
	data = aligned_ram[decimal_value]
	set_block_index_sum = configs['L1 #setBits'] + configs['L1 #blockBits']
	tag_binary = str(binary_value[:len(binary_value)-set_block_index_sum])
	set_value = '0'

	if configs['L1 #setBits'] != 0:
		set_value = str(binary_value[-set_block_index_sum:-configs['L1 #blockBits']])
		set_value = bin_to_dec(set_value)

	block_value = str(binary_value[-configs['L1 #blockBits']:])

	tag_binary = post_normalize_tag(tag_binary, 32 - set_block_index_sum)
	tag_hex = bin_to_hex(tag_binary)

	# Looking for L1I - Start
	isFound = False
	foundItem = ()
	for set_num, line_values in L1_instruction.items():
		for line_num, cache_value in line_values.items():
			if cache_value['tag'] == tag_hex and cache_value['v_bit'] == 1:
				isFound = True
				foundItem = (set_num, line_num)

	if isFound:
		performance['L1I hits'] += 1
		L1_instruction[foundItem[0]][foundItem[1]]['v_bit'] = 1
		L1_instruction[foundItem[0]][foundItem[1]]['tag'] = tag_hex
		L1_instruction[foundItem[0]][foundItem[1]]['time'] = L1I_time
		j = 0
		for i in range(0, int(size)*2, 2):
			L1_instruction[foundItem[0]][foundItem[1]]['block'][j] = data[i:i+2]
			j += 1
		L1I_time += 1
				
	else:
		performance['L1I misses'] += 1
		line_number = ''

		for line_num, value in L1_instruction[set_value].items():
			if value['v_bit'] == 0:
				line_number = line_num
				break
					
		if line_number != '':
			L1_instruction[set_value][line_number]['v_bit'] = 1
			L1_instruction[set_value][line_number]['tag'] = tag_hex
			L1_instruction[set_value][line_number]['time'] = L1I_time

			j = 0
			for i in range(0, len(data), 2):
				L1_instruction[set_value][line_number]['block'][j] = data[i:i+2]
				j += 1

			eviction_queue['L1I'][set_value].append(line_number)
			L1I_time += 1
		else:
			performance['L1I evictions'] += 1
			line_number = eviction_queue['L1I'][set_value].pop(0)
			L1_instruction[set_value][line_number]['v_bit'] = 1
			L1_instruction[set_value][line_number]['tag'] = tag_hex
			L1_instruction[set_value][line_number]['time'] = L1I_time

			j = 0
			for i in range(0, int(size)*2, 2):
				L1_instruction[set_value][line_number]['block'][j] = data[i:i+2]
				j += 1

			eviction_queue['L1I'][set_value].append(line_number)
			L1I_time += 1
	# Looking for L1I - End

	# Looking for L2 - Start
	isFound = False
	foundItem = ()
	for set_num, line_values in L2_cache.items():
		for line_num, cache_value in line_values.items():
			if cache_value['tag'] == tag_hex and cache_value['v_bit'] == 1:
				isFound = True
				foundItem = (set_num, line_num)

	if isFound:
		performance['L2 hits'] += 1
		L2_cache[foundItem[0]][foundItem[1]]['v_bit'] = 1
		L2_cache[foundItem[0]][foundItem[1]]['tag'] = tag_hex
		L2_cache[foundItem[0]][foundItem[1]]['time'] = L1I_time
		j = 0
		for i in range(0, int(size)*2, 2):
			L2_cache[foundItem[0]][foundItem[1]]['block'][j] = data[i:i+2]
			j += 1
		L1I_time += 1
				
	else:
		performance['L2 misses'] += 1
		line_number = ''

		for line_num, value in L2_cache[set_value].items():
			if value['v_bit'] == 0:
				line_number = line_num
				break
					
		if line_number != '':
			L2_cache[set_value][line_number]['v_bit'] = 1
			L2_cache[set_value][line_number]['tag'] = tag_hex
			L2_cache[set_value][line_number]['time'] = L1I_time

			j = 0
			for i in range(0, len(data), 2):
				L2_cache[set_value][line_number]['block'][j] = data[i:i+2]
				j += 1

			eviction_queue['L2'][set_value].append(line_number)
			L1I_time += 1
		else:
			performance['L2 evictions'] += 1
			line_number = eviction_queue['L2'][set_value].pop(0)
			L2_cache[set_value][line_number]['v_bit'] = 1
			L2_cache[set_value][line_number]['tag'] = tag_hex
			L2_cache[set_value][line_number]['time'] = L1I_time

			j = 0
			for i in range(0, int(size)*2, 2):
				L1_instruction[set_value][line_number]['block'][j] = data[i:i+2]
				j += 1

			eviction_queue['L2'][set_value].append(line_number)
			L2_time += 1
	# Looking for L2 - eND

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

	L1_data = create_cache(configs['L1 #sets'], configs['L1 lines/set'], configs['L1 block size'], L1_data, 'L1D')
	L1_instruction = create_cache(configs['L1 #sets'], configs['L1 lines/set'], configs['L1 block size'], L1_instruction, 'L1I')
	L2_cache = create_cache(configs['L2 #sets'], configs['L2 lines/set'], configs['L2 block size'], L2_cache, 'L2')

	aligned_ram = parse_memory(aligned_ram)

	L1I_time = 1
	L1D_time = 1
	L2_time = 1

	with open(trace_file) as tf:
		for line in tf:
			trace = line.replace(',', '').strip().split()
			address = trace[1]
			size = trace[2]
			if trace[0] == 'I':   # instruction load
				instruction_load(aligned_ram, address, size, L1_instruction, L2_cache, L1D_time, L2_time)
				
				print(L1_instruction)
				print(L2_cache)

			elif trace[0] == 'L':   # data load
				pass

			elif trace[0] == 'S':   # data store
				data = trace[3]

			elif trace[0] == 'M':   # data load and then data store
				data = trace[3]
	
	# printing the performance of each cache at the end of trace
	print('L1I-hits:{} L1I-misses:{} L1I-evictions:{}'.format(performance['L1I hits'], performance['L1I misses'], performance['L1I evictions']))
	print('L1D-hits:{} L1D-misses:{} L1D-evictions:{}'.format(performance['L1D hits'], performance['L1D misses'], performance['L1D evictions']))
	print('L2-hits:{} L2-misses:{} L2-evictions:{}'.format(performance['L2 hits'], performance['L2 misses'], performance['L2 evictions']))

	# exporting the content of caches to separate files
	with open('L1-instruction.txt', 'w') as fw:
		json.dump(L1_instruction, fw, indent=4, sort_keys=True)

	with open('L1-data.txt', 'w') as fw:
		json.dump(L1_data, fw, indent=4, sort_keys=True)

	with open('L2.txt', 'w') as fw:
		json.dump(L2_cache, fw, indent=4, sort_keys=True)

main()


