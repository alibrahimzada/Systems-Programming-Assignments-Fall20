# Full Name: Ali Reza Ibrahimzada
# Student Number: 150119870

# this dictionary holds the mapping between hexadecimal representation and 4-bit binaries
hex_binary = {'0': '0000', '1': '0001', '2': '0010', '3': '0011', '4': '0100', '5': '0101', '6': '0110', '7': '0111', 
              '8': '1000', '9': '1001', 'A': '1010', 'B': '1011', 'C': '1100', 'D': '1101', 'E': '1110', 'F': '1111'}

# this function acts as the control unit, that is, it calls other functions
def main():
    while True:   # this infinite loop will break once the hexadecimal number is validated
        hex_number = input('Enter a hex number: ')   # first the user is prompted to enter a hex number
        if not hex_number:   # if nothing has been entered, then the program gives an error and asks again
            print('error: no hex number has been provided')
            continue

        # this function justifies the hex number if it has odd number of characters
        even_hex = justify_number(hex_number)

        try:   # this block catches the exception raised by validate_number function, if any
            validated_hex = validate_number(even_hex)
            break
        except Exception as ex:
            print(ex)
            continue

    while True:   # this infinite loop will break once the data type is validated
        data_type = input('Data type: ')   # at this point the user is prompted to enter the data type

        # in this condition, we check if the data type is valid        
        if data_type not in ['F', 'S', 'U']:
            print('error: data type is invalid!')
            continue
        break

    # from here, the branching of the program starts based on the provided data type
    if data_type == 'S':
        decimal_number = convert_integer(validated_hex, signed=True)
    elif data_type == 'U':
        decimal_number = convert_integer(validated_hex)
    elif data_type == 'F':
        decimal_number = convert_float(validated_hex)

    print(decimal_number)   # the program prints the output and terminates here

# this function justifies the number of characters in a string to even
def justify_number(hex_number):
    if len(hex_number) % 2 == 0:    # if its already justified, we do not touch it
        return hex_number

    # else we add a 0 as the most significant bit and return it
    justified_number = '0' + hex_number[:]
    return justified_number

# this function raises an exception if any of the characters in hex number are invalid
# or its bigger than 4 bytes
def validate_number(even_hex):
    for char in even_hex:
        if char not in hex_binary:   # this condition checks for invalid characters in the input
            raise Exception('error: input contains an invalid character!')

    if len(even_hex) > 8:   # this condition checks if the input size is bigger than 4 bytes
        raise Exception('error: input is bigger than 4 bytes!')
    
    return even_hex

# this function converts the input into either a sign or unsign integer
def convert_integer(hex_number, signed=False):
    decimal_number = 0
    binary_number = ''
    start_index = 0

    # first we start by building the binary representation of the hexadecimal number
    for char in hex_number:
        binary_number += hex_binary[char]

    # then we check if the user wants to convert the hex number into a signed integer
    if binary_number[0] == '1' and signed:
        # if so, we calculate the decimal of the most significant bit
        decimal_number = -2**(len(binary_number) - 1)
        start_index += 1

    # this loop sums the integer representation of each bit
    for i in range(start_index, len(binary_number)):
        decimal_number += int(binary_number[i]) * (2**(len(binary_number) - 1 - i))

    return decimal_number

# this function converts the input into a floating point number
def convert_float(hex_number):
    decimal_number = 0
    binary_number = ''

    # first we start by building the binary representation of the hexadecimal number
    for char in hex_number:
        binary_number += hex_binary[char]
    
    sign_bit = binary_number[0]   # then we get the sign bit and update the binary number
    binary_number = binary_number[1:]
    exponent_binary, binary_number = get_exponent(binary_number)   # we get the exponent bits and update the binary number

    # this condition checks for NaN special case
    if '0' not in exponent_binary and '1' in binary_number:
        return 'NaN'

    # this condition checks for infinity special case
    elif '0' not in exponent_binary and '1' not in binary_number:
        if sign_bit == '0':
            return '+∞'
        else:
            return '-∞'

    # this condition checks for numbers very close to 0
    elif '1' not in exponent_binary and '1' not in binary_number:
        if sign_bit == '0':
            return '+0'
        else:
            return '-0'

    bias = get_bias(exponent_binary)   # we calculate the bias based on the length of exponent bits
    fraction_binary = get_fraction(binary_number)   # we get the fraction/rounded fraction (only for 3 and 4 bytes input)

    # this condition checks if floating point number is normalized
    if '1' in exponent_binary and '0' in exponent_binary:
        mantissa = 1 + bin_to_dec(fraction_binary, fraction=True)
        exp = bin_to_dec(exponent_binary)
        decimal_number = (-1)**int(sign_bit) * mantissa * 2**(exp - bias)
    
    # this condition checks if floating point number is denormalized
    elif '1' not in exponent_binary and '1' in fraction_binary:
        mantissa = bin_to_dec(fraction_binary, fraction=True)
        exp = bin_to_dec(exponent_binary)
        decimal_number = (-1)**int(sign_bit) * mantissa * 2**(1 - bias)

    # these conditions round the floating point's decimal representation
    if 'e' in str(decimal_number):
        decimal_number = "{res:.5e}".format(res=decimal_number)
    elif len(str(decimal_number).split('.')[1]) > 5:
        decimal_number = "{res:.5f}".format(res=decimal_number)
    return decimal_number

# this function finds the exponent bits and update the binary number
def get_exponent(binary_number):
    if len(binary_number) == 7:   # 1 byte input
        return binary_number[:4], binary_number[4:]
    elif len(binary_number) == 15:   # 2 byte input
        return binary_number[:6], binary_number[6:]
    elif len(binary_number) == 23:   # 3 byte input
        return binary_number[:8], binary_number[8:]
    else:   # 4 byte input
        return binary_number[:10], binary_number[10:]

# this function finds the bias based on the exponent bits length
def get_bias(exponent_binary):
    return 2**(len(exponent_binary) - 1) - 1

# this function returns the fraction part of the binary number
def get_fraction(binary_number):
    if len(binary_number) == 3 or len(binary_number) == 9:   # for 1 and 2 byte inputs, we do not round anything
        return binary_number
    elif len(binary_number) == 15 or len(binary_number) == 21:   # for inputs bigger than 2 bytes, we round to even
        rounded_fraction = round_bin(binary_number)
        return rounded_fraction

# this function changes a binary number to a decimal number
def bin_to_dec(binary_number, fraction=False):
    sum_ = 0
    if fraction:   # if the user wants to change a fraction binary to decimal
        for i in range(len(binary_number)):
            sum_ += int(binary_number[i]) * (2**(-i-1))
        return sum_

    for i in range(len(binary_number)):   # if the user wants to change non-fraction binary to decimal
        sum_ += int(binary_number[i]) * (2**(len(binary_number) - i - 1))
    return sum_

def round_bin(binary_number):
    # smaller than halfway case
    if binary_number[13] == '0':
        return binary_number[:13]
    
    # bigger than halfway case
    elif binary_number[13] == '1' and '1' in binary_number[14:]:
        return add_one_bin(binary_number[:13])
    
    # halfway case
    elif binary_number[13] == '1' and '1' not in binary_number[14:]:
        # if the first 13 bit are already even, we do not add 1
        if binary_number[12] == '0':
            return binary_number[:13]
        # otherwise, we add 1 to 13 bit binary
        else:
            return add_one_bin(binary_number[:13])

# this function adds 1 to the given binary number
def add_one_bin(binary_number):
    carry = 1
    sum_ = ''
    # first we loop over each bit in the given binary number
    for i in range(len(binary_number)):
        bit = int(binary_number[len(binary_number) - i - 1])    # get the next LSB in each iteration
        if bit == 1 and carry == 1:   # the condition checks when carry and bit are both 1
            sum_ += '0'
            carry = 1
        elif (bit == 0 and carry == 1) or (bit == 1 and carry == 0):   # the condition checks when either carry or bit is 1
            sum_ += '1'
            carry = 0
        elif (bit == 0 and carry == 0):   # the condition checks when both bit and carry are 0
            sum_ += '0'
            carry = 0

    return sum_[::-1]   # reverse the string at the end

if __name__ == "__main__":
    main()
