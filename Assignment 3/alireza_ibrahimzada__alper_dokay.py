import sys
import math
import json

hex_binary = {'0': '0000', '1': '0001', '2': '0010', '3': '0011', '4': '0100', '5': '0101', '6': '0110', '7': '0111', 
              '8': '1000', '9': '1001', 'A': '1010', 'B': '1011', 'C': '1100', 'D': '1101', 'E': '1110', 'F': '1111'}

binary_hex = {'0000': '0', '0001': '1', '0010': '2', '0011': '3', '0100': '4', '0101': '5', '0110': '6', '0111': '7',
			  '1000': '8', '1001': '9', '1010': 'A', '1011': 'B', '1100': 'C', '1101': 'D', '1110': 'E', '1111': 'F'}

configs = {'L1 #sets': 0, 'L1 lines/set': 0, 'L1 block size': 0, 'L1 #setBits': 0, 'L1 #blockBits': 0,
		   'L2 #sets': 0, 'L2 lines/set': 0, 'L2 block size': 0, 'L2 #setBits': 0, 'L2 #blockBits': 0}

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

def normalize_address(decimal_address):
	hex_address = list(hex(decimal_address).upper())[2:]   # clean the hex value from initial 0x
	while len(hex_address) != 8:
		hex_address.insert(0, '0')
	return ''.join(hex_address)

def parse_memory(aligned_ram):
	memory_image = ''
	with open('ram.txt') as ram:
		memory_image = ram.readlines()[0].replace(' ', '')
	
	byte_size = 8
	bits_per_hex = 4
	max_segment_size = (byte_size * configs['L1 block size']) // bits_per_hex
	index = 0
	for i in range(len(memory_image)):
		if i % max_segment_size == 0:
			address = normalize_address(index)
			aligned_ram.setdefault(address, memory_image[i-max_segment_size:i])
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
	if len(tag_value) == tag_length and tag_length % 4 == 0:
		return tag_value

	while (tag_length % 4 != 0):
		tag_length -= 1
	
	new_tag_value = tag_value[-tag_length:]

	return new_tag_value

def load(aligned_ram, address, size, L1_cache, L2_cache, cache_name):
	## ALPER, IN LOAD IN ORDER TO MAKE PRINTS CONSISTENT WITH BIROL WANTS. PLEASE SEE THE MANUAL. MISSES ARE 
	## BEING PRINTED IN LINE 1, THEN PLACE IN L2, THEN PLACE IN L1D/I. THANKS.
	binary_value = hex_to_bin(address)   # converting the hexadecimal address to its binary form

	if len(binary_value) != 32:
		binary_value = (32 - len(binary_value)) * '0' + binary_value

	address = bin_to_hex(binary_value)  # taking the address in hex format
	aligned_ram.setdefault(address, '0' * (configs['L1 block size'] * 2))   # set the value of an address higher than maximum representable address	
	data = aligned_ram[address]   # retrieving the data from the RAM

	# L1 cache based variable declarations - Start
	set_block_index_sum_l1 = configs['L1 #setBits'] + configs['L1 #blockBits']   # adding the total number of bits for set and block
	tag_binary_l1 = str(binary_value[:len(binary_value)-set_block_index_sum_l1])   # extracting the binary tag from the address
	set_value_l1 = '0'
	block_value_l1 = int(bin_to_dec(str(binary_value[-configs['L1 #blockBits']:])))

	if configs['L1 #setBits'] != 0:   # checking if there is a bit to represent set
		set_value_l1 = str(binary_value[-set_block_index_sum_l1:-configs['L1 #blockBits']])
		set_value_l1 = bin_to_dec(set_value_l1)

	tag_binary_l1 = post_normalize_tag(tag_binary_l1, 32 - set_block_index_sum_l1)
	tag_hex_l1 = bin_to_hex(tag_binary_l1)
	# L1 cache based variable declarations - End


	# Looking for L1 - Start
	isFound = False
	# TODO: Starting address should be fetched from block decimal
	if set_value_l1 in L1_cache:
		for line_num, cache_value in L1_cache[set_value_l1].items():
			if cache_value['tag'] == tag_hex_l1 and cache_value['v_bit'] == 1:
				isFound = True
				break

	if isFound:
		print(cache_name + ' hit, ', end='')
		performance[cache_name + ' hits'] += 1
				
	else:
		print(cache_name + ' miss, ', end='')
		performance[cache_name + ' misses'] += 1
		line_number = ''

		for line_num, value in L1_cache[set_value_l1].items():   # this condition will check if there is an empty line available
			if value['v_bit'] == 0:
				line_number = line_num
				break
					
		if line_number != '':   # if there exists an empty line, then:
			L1_cache[set_value_l1][line_number]['v_bit'] = 1
			L1_cache[set_value_l1][line_number]['tag'] = tag_hex_l1
			L1_cache[set_value_l1][line_number]['time'] += 1

			j = 0
			for i in range(0, len(data), 2):
				L1_cache[set_value_l1][line_number]['block'][j] = data[i:i+2]
				j += 1

			eviction_queue[cache_name][set_value_l1].append(line_number)

		else:   # if there are no empty lines, then an eviction happens
			performance[cache_name + ' evictions'] += 1
			line_number = eviction_queue[cache_name][set_value_l1].pop(0)
			# alper we should use <del> here to delete the key-value pair of poped line
			L1_cache[set_value_l1][line_number]['v_bit'] = 1
			L1_cache[set_value_l1][line_number]['tag'] = tag_hex_l1
			L1_cache[set_value_l1][line_number]['time'] += 1

			j = block_value_l1
			for i in range(block_value_l1*2, block_value_l1*2 + int(size)*2, 2):
				if i < len(data):
					L1_cache[set_value_l1][line_number]['block'][j] = data[i:i+2]
					j += 1
					continue
				break

			eviction_queue[cache_name][set_value_l1].append(line_number)
	# Looking for L1I - End

	# Looking for L2 - Start

	# L2 cache based variable declarations - Start
	set_block_index_sum_l2 = configs['L2 #setBits'] + configs['L2 #blockBits']   # adding the total number of bits for set and block
	tag_binary_l2 = str(binary_value[:len(binary_value)-set_block_index_sum_l2])   # extracting the binary tag from the address
	set_value_l2 = '0'
	block_value_l2 = int(bin_to_dec(str(binary_value[-configs['L2 #blockBits']:])))

	if configs['L2 #setBits'] != 0:   # checking if there is a bit to represent set
		set_value_l2 = str(binary_value[-set_block_index_sum_l2:-configs['L2 #blockBits']])
		set_value_l2 = bin_to_dec(set_value_l2)

	tag_binary_l2 = post_normalize_tag(tag_binary_l2, 32 - set_block_index_sum_l2)
	tag_hex_l2 = bin_to_hex(tag_binary_l2)
	# L2 cache based variable declarations - End

	isFound = False
	# TODO: Starting address should be fetched from block decimal
	if set_value_l2 in L2_cache:
		for line_num, cache_value in L2_cache[set_value_l2].items():
			if cache_value['tag'] == tag_hex_l2 and cache_value['v_bit'] == 1:
				isFound = True
				break

	if isFound:
		print('L2 hit, ')
		performance['L2 hits'] += 1

	else:
		print('L2 miss')
		performance['L2 misses'] += 1
		line_number = ''

		for line_num, value in L2_cache[set_value_l2].items():   # this condition will check if there is an empty line available
			if value['v_bit'] == 0:
				line_number = line_num
				break
					
		if line_number != '':   # if there exists an empty line, then:
			L2_cache[set_value_l2][line_number]['v_bit'] = 1
			L2_cache[set_value_l2][line_number]['tag'] = tag_hex_l2
			L2_cache[set_value_l2][line_number]['time'] += 1

			j = 0
			for i in range(0, len(data), 2):
				L2_cache[set_value_l2][line_number]['block'][j] = data[i:i+2]
				j += 1

			eviction_queue['L2'][set_value_l2].append(line_number)

		else:   # if there are no empty lines, then an eviction happens
			performance['L2 evictions'] += 1
			line_number = eviction_queue['L2'][set_value_l2].pop(0)
			# alper we should use <del> here to delete the key-value pair of poped line
			L2_cache[set_value_l2][line_number]['v_bit'] = 1
			L2_cache[set_value_l2][line_number]['tag'] = tag_hex_l2
			L2_cache[set_value_l2][line_number]['time'] += 1

			j = block_value_l2 - 1
			for i in range(block_value_l2*2, block_value_l2*2 + int(size)*2, 2):
				if i < len(data):
					L2_cache[set_value_l2][line_number]['block'][j] = data[i:i+2]
					j += 1
					continue
				break

			eviction_queue['L2'][set_value_l2].append(line_number)


	# Looking for L2 - end

def store(aligned_ram, address, size, data, L1_data, L2_cache):
	binary_value = hex_to_bin(address)   # converting the hexadecimal address to its binary form

	if len(binary_value) != 32:
		binary_value = (32 - len(binary_value)) * '0' + binary_value

	address = bin_to_hex(binary_value)  # taking the address in hex format
	aligned_ram.setdefault(address, '0' * (configs['L1 block size'] * 2))   # set the value of an address higher than maximum representable address

	# <write-hit>

	set_block_index_sum_l1 = configs['L1 #setBits'] + configs['L1 #blockBits']   # adding the total number of bits for set and block
	tag_binary_l1 = str(binary_value[:len(binary_value)-set_block_index_sum_l1])   # extracting the binary tag from the address
	set_value_l1 = '0'
	block_value_l1 = int(bin_to_dec(str(binary_value[-configs['L1 #blockBits']:])))

	if configs['L1 #setBits'] != 0:   # checking if there is a bit to represent set
		set_value_l1 = str(binary_value[-set_block_index_sum_l1:-configs['L1 #blockBits']])
		set_value_l1 = bin_to_dec(set_value_l1)

	tag_binary_l1 = post_normalize_tag(tag_binary_l1, 32 - set_block_index_sum_l1)
	tag_hex_l1 = bin_to_hex(tag_binary_l1)

	# L2 cache based variable declarations - Start
	set_block_index_sum_l2 = configs['L2 #setBits'] + configs['L2 #blockBits']   # adding the total number of bits for set and block
	tag_binary_l2 = str(binary_value[:len(binary_value)-set_block_index_sum_l2])   # extracting the binary tag from the address
	set_value_l2 = '0'
	block_value_l2 = int(bin_to_dec(str(binary_value[-configs['L2 #blockBits']:])))

	if configs['L2 #setBits'] != 0:   # checking if there is a bit to represent set
		set_value_l2 = str(binary_value[-set_block_index_sum_l2:-configs['L2 #blockBits']])
		set_value_l2 = bin_to_dec(set_value_l2)

	tag_binary_l2 = post_normalize_tag(tag_binary_l2, 32 - set_block_index_sum_l2)
	tag_hex_l2 = bin_to_hex(tag_binary_l2)
	# L2 cache based variable declarations - End
	
	isFound_L1 = False
	line_number_L1 = ''
	if set_value_l1 in L1_data:
		for line_num, cache_value in L1_data[set_value_l1].items():
			if cache_value['tag'] == tag_hex_l1 and cache_value['v_bit'] == 1:
				isFound_L1 = True
				line_number_L1 = line_num
				break
	
	isFound_L2 = False
	line_number_L2 = ''
	if set_value_l2 in L2_cache:
		for line_num, cache_value in L2_cache[set_value_l2].items():
			if cache_value['tag'] == tag_hex_l2 and cache_value['v_bit'] == 1:
				isFound_L2 = True
				line_number_L2 = line_num
				break

	if isFound_L1:
		print('L1D hit, ', end='')
		performance['L1D hits'] += 1

		# L1 Cache Update - Start 
		j = 0
		if block_value_l1 != 0:
			j = block_value_l1 - 1
		for i in range(int(size)):
			L1_data[set_value_l1][line_number_L1]['block'][j] = data[i:i+2].upper()
			j += 1
		# L1 Cache Update - End
		
		aligned_ram[address] = ''.join(L1_data[set_value_l1][line_number_L1]['block'])  # RAM Update
		
	else:
		print('L1D miss, ', end='')
		performance['L1D misses'] += 1

		j = 0
		if block_value_l2 != 0:
			j = block_value_l2 - 1
		# RAM Update - Start
		# temp = L1_data[set_value_l1][line_number_L1D]['block']
		temp = aligned_ram[address]
		for i in range(int(size)):
			temp[j] = data[i:i+2]
			j += 1
		aligned_ram[address] = ''.join(temp)

	# L2
	if isFound_L2:
		print('L2 hit, ', end='')
		performance['L2 hits'] += 1
		# L2 Cache Update - Start
		j = 0
		if block_value_l2 != 0:
			j = block_value_l2 - 1
		for i in range(int(size)):
			L2_cache[set_value_l2][line_number_L2]['block'][j] = data[i:i+2].upper()
			j += 1
		# L2 Cache Update - End
	else:
		print('L2 miss, ', end='')
		performance['L2 misses'] += 1
		pass

	# </write-hit>

	# <write-miss>
	# same thing as above... let's refactor here
	# </write-miss>

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

	with open(trace_file) as tf:
		for line in tf:
			print(line, end='')
			trace = line.replace(',', '').strip().split()
			address = trace[1]
			size = trace[2]
			if trace[0] == 'I':   # instruction load
				load(aligned_ram, address, size, L1_instruction, L2_cache, 'L1I')

			elif trace[0] == 'L':   # data load
				load(aligned_ram, address, size, L1_data, L2_cache, 'L1D')

			elif trace[0] == 'S':   # data store
				data = trace[3]
				store(aligned_ram, address, size, data, L1_data, L2_cache)

			elif trace[0] == 'M':   # data load and then data store
				data = trace[3]
				
	# if you want to see if it is working or not, check the following print statements with manual.trace
	# START
	# print(L1_instruction)
	# print("------------------------------")
	# print(L1_data)
	# print("------------------------------")
	# print(L2_cache)
	# print("------------------------------")
	# print(aligned_ram["00000000"])
	# END

	# printing the performance of each cache at the end of trace
	print('\nL1I-hits:{} L1I-misses:{} L1I-evictions:{}'.format(performance['L1I hits'], performance['L1I misses'], performance['L1I evictions']))
	print('L1D-hits:{} L1D-misses:{} L1D-evictions:{}'.format(performance['L1D hits'], performance['L1D misses'], performance['L1D evictions']))
	print('L2-hits:{} L2-misses:{} L2-evictions:{}'.format(performance['L2 hits'], performance['L2 misses'], performance['L2 evictions']))

	# exporting the content of caches to separate files
	# with open('L1-instruction.txt', 'w') as fw:
	# 	json.dump(L1_instruction, fw, indent=4, sort_keys=True)

	# with open('L1-data.txt', 'w') as fw:
	# 	json.dump(L1_data, fw, indent=4, sort_keys=True)

	# with open('L2.txt', 'w') as fw:
	# 	json.dump(L2_cache, fw, indent=4, sort_keys=True)

main()
