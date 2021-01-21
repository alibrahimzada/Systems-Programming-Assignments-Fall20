import sys
import math
import json

L1_data = {}   # we consider the L1 data cache as a dictionary. The complete structure is defined in create_cache() function
L1_instruction = {}   # we consider the L1 instruction cache as a dictionary. The complete structure is defined in create_cache() function
L2_cache = {}   # we consider the L2 cache as a dictionary. The complete structure is defined in create_cache() function
aligned_ram = {}   # we align the given memory image based on the cache block size, and store it as a key-value (address-data) pair

# the following two dictionaries are mappers which helps us in conversions
hex_binary = {'0': '0000', '1': '0001', '2': '0010', '3': '0011', '4': '0100', '5': '0101', '6': '0110', '7': '0111', 
              '8': '1000', '9': '1001', 'A': '1010', 'B': '1011', 'C': '1100', 'D': '1101', 'E': '1110', 'F': '1111'}

binary_hex = {binary: hexa for hexa, binary in hex_binary.items()}

# the configs dictionary stores the initial configuration of caches given as command line arguments
configs = {'L1 #sets': 0, 'L1 lines/set': 0, 'L1 block size': 0, 'L1 #setBits': 0, 'L1 #blockBits': 0,
		   'L2 #sets': 0, 'L2 lines/set': 0, 'L2 block size': 0, 'L2 #setBits': 0, 'L2 #blockBits': 0}

# the eviction queue dictionary stores the order of lines in each cache and maintains FIFO
eviction_queue = {'L1D': {}, 'L1I': {}, 'L2': {}}

# the performance dictionary helps us to keep track of cache performance throughout the simulation
performance = {'L1I hits': 0, 'L1I misses': 0, 'L1I evictions': 0,
			   'L1D hits': 0, 'L1D misses': 0, 'L1D evictions': 0,
			   'L2 hits': 0, 'L2 misses': 0, 'L2 evictions': 0}

time = {'global time': 0}

def parse_arguments(args):   # this function parses the command line arguments
	trace_file = ''
	for i in range(len(args)):   # loop over all arguments, use specific keywords to get cache settings
		if args[i] == '-L1s':
			configs['L1 #sets'] = int(math.pow(2, int(args[i + 1])))
			configs['L1 #setBits'] = int(args[i + 1])   # bits stored for substring process in each operation
		elif args[i] == '-L1E':
			configs['L1 lines/set'] = int(args[i + 1])
		elif args[i] == '-L1b':
			configs['L1 block size'] = int(math.pow(2, int(args[i + 1])))
			configs['L1 #blockBits'] = int(args[i + 1])   # bits stored for substring process in each operation
		elif args[i] == '-L2s':
			configs['L2 #sets'] = int(math.pow(2, int(args[i + 1])))
			configs['L2 #setBits'] = int(args[i + 1])   # bits stored for substring process in each operation
		elif args[i] == '-L2E':
			configs['L2 lines/set'] = int(args[i + 1])
		elif args[i] == '-L2b':
			configs['L2 block size'] = int(math.pow(2, int(args[i + 1])))
			configs['L2 #blockBits'] = int(args[i + 1])   # bits stored for substring process in each operation
		elif args[i] == '-t':
			trace_file = args[i + 1]
	return trace_file

def create_cache(total_sets, total_lines, block_size, cache, cache_name):   # this function creates caches based on command line arguments
	"""
	the caches are stored in the following way for better manipulation:

	{set_number:
		{line number:
			{
				v_bit: 0/1,
				time : 0,
				tag: '',
				block: [byte_1, ...]
			}, ...
		}, ...
	}
	"""
	for i in range(total_sets):   # i represents a set number, starting from 0
		cache.setdefault(str(i), {})
		eviction_queue[cache_name].setdefault(str(i), [])   # create a list for set i in cache in order to maintain FIFO
		for j in range(total_lines):   # j represents a line number in set i
			cache[str(i)].setdefault(str(j), {'v_bit': 0, 'tag': '', 'time': 0, 'block': []})
			for k in range(block_size):   # k represents a block in line j and set i, which is empty in the beginning
				cache[str(i)][str(j)]['block'].append('')

def normalize_address(decimal_address):   # this function normalizes a given decimal address to 8 digit hex-address
	hex_address = list(hex(decimal_address).upper())[2:]   # clean the hex value from initial 0x
	while len(hex_address) != 8:   # create an eight digit hex address but adding zeros to the left
		hex_address.insert(0, '0')
	return ''.join(hex_address)   # return the normalized hex address

def parse_memory():   # this function aligns the memory image according to cache block size
	memory_image = ''
	with open('ram.txt') as ram:   # please put the ram.txt in the same directory as .py file
		memory_image = ram.readlines()[0].replace(' ', '')   # remove all space characters
	
	byte_size = 8
	bits_per_hex = 4
	max_segment_size = (byte_size * configs['L1 block size']) // bits_per_hex   # calculate the maximum alignment size
	index = 0
	for i in range(len(memory_image)):   # loop over memory image and align data into addresses
		if i % max_segment_size == 0:
			address = normalize_address(index)
			aligned_ram.setdefault(address, memory_image[i-max_segment_size:i])
			index += 1

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

def post_normalize_tag(tag_value, tag_length):   # this function makes sure we have the right number of bits in tag
	if len(tag_value) == tag_length and tag_length % 4 == 0:   # if its correct, return the given value
		return tag_value

	while (tag_length % 4 != 0):   # remove the bits from left most to make it divisible by 4
		tag_length -= 1
	
	new_tag_value = tag_value[-tag_length:]
	return new_tag_value

def process_trace_address(address):   # this function processes a given hex address, and normalizes it if necessary
	binary_value = hex_to_bin(address)   # converting the hexadecimal address to its binary form

	if len(binary_value) != 32:   # normalize the address to 32 bits, if its not already normalized
		binary_value = (32 - len(binary_value)) * '0' + binary_value

	address = bin_to_hex(binary_value)   # converting the normalized address back in hex format
	aligned_ram.setdefault(address, '0' * (configs['L1 block size'] * 2))   # set the value of an address higher than maximum representable address	
	data = aligned_ram[address]   # retrieving the data from the RAM

	return binary_value, data, address

def manipulate_trace_address(cache_name, binary_value):   # this function calculates the set, block and tag values from a given binary address
	set_block_index_sum = configs[cache_name +' #setBits'] + configs[cache_name + ' #blockBits']   # adding the total number of bits for set and block
	tag_binary = str(binary_value[:len(binary_value)-set_block_index_sum])   # extracting the binary tag from the address
	set_value = '0'   # setting default set value
	block_value = int(bin_to_dec(str(binary_value[-configs[cache_name + ' #blockBits']:])))   # calculating block value from block bits

	if configs[cache_name + ' #setBits'] != 0:   # checking if there is a bit to represent set
		set_value = str(binary_value[-set_block_index_sum:-configs[cache_name + ' #blockBits']])
		set_value = bin_to_dec(set_value)

	tag_binary = post_normalize_tag(tag_binary, 32 - set_block_index_sum)   # post normalize tag
	tag_hex = bin_to_hex(tag_binary)   # convert tag to hexadecimal

	return set_value, block_value, tag_hex

def is_hit(set_value, cache, tag_hex):   # this function looks a cache for a possible hit
	isFound = False
	line_number = ''
	if set_value in cache:   # if set value is not in cache, return false
		for line_num, cache_value in cache[set_value].items():   # for all lines in the given set
			if cache_value['tag'] == tag_hex and cache_value['v_bit'] == 1:   # if valid bit is 1, and tag matches, then return true
				isFound = True
				line_number = line_num
				break
	return isFound, line_number

def process_load_miss(cache_name, cache, set_value, tag_hex, data, block_value, size):
	performance[cache_name + ' misses'] += 1
	line_number = ''

	for line_num, value in cache[set_value].items():   # this condition will check if there is an empty line available
		if value['v_bit'] == 0:
			line_number = line_num
			break
				
	if line_number != '':   # if there exists an empty line, then:
		j = 0
		for i in range(0, len(data), 2):
			cache[set_value][line_number]['block'][j] = data[i:i+2]
			j += 1

	else:   # if there are no empty lines, then an eviction happens
		performance[cache_name + ' evictions'] += 1
		line_number = eviction_queue[cache_name][set_value].pop(0)

		j = block_value
		for i in range(block_value * 2, block_value * 2 + int(size) * 2, 2):
			if i < len(data):
				cache[set_value][line_number]['block'][j] = data[i:i+2]
				j += 1
				continue
			break

	print('{} miss, Place in {} set {}'.format(cache_name, cache_name, set_value))

	cache[set_value][line_number]['v_bit'] = 1
	cache[set_value][line_number]['tag'] = tag_hex
	if cache_name != 'L2':
		time['global time'] += 1
	cache[set_value][line_number]['time'] = time['global time']
	eviction_queue[cache_name][set_value].append(line_number)

def load(address, size, L1_cache, cache_name):   # this function implements the load operation
	binary_value, data, address = process_trace_address(address)
	set_value_l1, block_value_l1, tag_hex_l1 = manipulate_trace_address('L1', binary_value)
	set_value_l2, block_value_l2, tag_hex_l2 = manipulate_trace_address('L2', binary_value)

	isFound_L1, line_number = is_hit(set_value_l1, L1_cache, tag_hex_l1)
	isFound_L2, line_number = is_hit(set_value_l2, L2_cache, tag_hex_l2)

	if isFound_L1:
		print(cache_name + ' hit, ', end='')
		performance[cache_name + ' hits'] += 1

	if isFound_L2:
		print('L2 hit')
		performance['L2 hits'] += 1

	if not isFound_L1:
		process_load_miss(cache_name, L1_cache, set_value_l1, tag_hex_l1, data, block_value_l1, size)

	if not isFound_L2:
		process_load_miss('L2', L2_cache, set_value_l2, tag_hex_l2, data, block_value_l2, size)

def store(address, size, data):
	binary_value, ram_data, address = process_trace_address(address)
	set_value_l1, block_value_l1, tag_hex_l1 = manipulate_trace_address('L1', binary_value)
	set_value_l2, block_value_l2, tag_hex_l2 = manipulate_trace_address('L2', binary_value)
	
	isFound_L1, line_number_L1 = is_hit(set_value_l1, L1_data, tag_hex_l1)
	isFound_L2, line_number_L2 = is_hit(set_value_l2, L2_cache, tag_hex_l2)

	if isFound_L1:
		print('L1D hit, Store in L1D, RAM')
		performance['L1D hits'] += 1

		j = 0
		if block_value_l1 != 0:
			j = block_value_l1 - 1
		for i in range(int(size)):
			L1_data[set_value_l1][line_number_L1]['block'][j] = data[i:i+2].upper()   # L1D update
			j += 1
		
		aligned_ram[address] = ''.join(L1_data[set_value_l1][line_number_L1]['block'])  # RAM update
		
	else:
		print('L1D miss, Store in RAM')
		performance['L1D misses'] += 1

		j = 0
		if block_value_l2 != 0:
			j = block_value_l2 - 1

		temp = aligned_ram[address]
		for i in range(int(size) * 2):
			temp = temp[:j] + data[i] + temp[j+1:]
			j += 1
		aligned_ram[address] = temp   # RAM‌ update

	if isFound_L2:
		print('L2 hit, Store in L2')
		performance['L2 hits'] += 1

		j = 0
		if block_value_l2 != 0:
			j = block_value_l2 - 1
		for i in range(int(size)):
			L2_cache[set_value_l2][line_number_L2]['block'][j] = data[i:i+2].upper()   # L2 update
			j += 1

	else:
		print('L2 miss')
		performance['L2 misses'] += 1

def main():   # the main function starts the programming by initializing the caches, read the trace file, and exporting the output
	args = sys.argv
	if len(args) != 15:   # this condition makes sure we get the right number of command line arguments
		print("insufficient number of arguments. exiting the program")
		return 1

	trace_file = parse_arguments(args)   # this function call parses the command line arguments, fills the necessary data structures, and returns the
										 # name of the trace file

	# the following function calls create 3 caches based on the configurations given in command line
	create_cache(configs['L1 #sets'], configs['L1 lines/set'], configs['L1 block size'], L1_data, 'L1D')
	create_cache(configs['L1 #sets'], configs['L1 lines/set'], configs['L1 block size'], L1_instruction, 'L1I')
	create_cache(configs['L2 #sets'], configs['L2 lines/set'], configs['L2 block size'], L2_cache, 'L2')

	parse_memory()   # this function aligns the memory image and updates the align ram dictionary

	with open(trace_file) as tf:   # open the given trace file
		for line in tf:   # loop over each line in trace file
			print('\n' + line, end='')
			trace = line.replace(',', '').strip().split()   # tokenize the line
			address = trace[1]   # get the address
			size = trace[2]   # get the size
			if trace[0] == 'I':   # instruction load
				load(address, size, L1_instruction, 'L1I')   # this function calls the load operation on L1 instruction

			elif trace[0] == 'L':   # data load
				load(address, size, L1_data, 'L1D')   # this function calls the load operation on L1 data

			elif trace[0] == 'S':   # data store
				data = trace[3]   # get the given data
				store(address, size, data)   # this function calls the store operation on L1 data

			elif trace[0] == 'M':   # data load and then data store
				data = trace[3]
				load(address, size, L1_data, 'L1D')   # this function calls the load operation on L1 data
				store(address, size, data)   # this function calls the store operation on L1 data
				
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
	with open('L1-instruction.txt', 'w') as fw:
		json.dump(L1_instruction, fw, indent=4, sort_keys=True)

	with open('L1-data.txt', 'w') as fw:
		json.dump(L1_data, fw, indent=4, sort_keys=True)

	with open('L2.txt', 'w') as fw:
		json.dump(L2_cache, fw, indent=4, sort_keys=True)

main()
