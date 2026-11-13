import base64

# Address constants from the decompiled code
STAGE2_STRING_ADDR = 0x004890c0  # "bewaretheidesofmarch"
STAGE2_CAESAR_KEY = 13          # 0xd from the code

STAGE3_BASE64_ADDR = 0x00489188  # Base64 encoded string


def read_null_terminated_string(address):
    """
    Reads a null-terminated string from memory at the given address
    """
    result = []
    offset = 0
    
    while True:
        byte = getByte(address.add(offset))
        if byte == 0:
            break
        # Handle signed byte conversion
        if byte < 0:
            byte = byte & 0xFF
        result.append(chr(byte))
        offset += 1
        
        # Safety limit to prevent infinite loops
        if offset > 1000:
            print("Warning: String too long, truncating at 1000 characters")
            break
    
    return ''.join(result)


def caesar_decrypt(encrypted, key):
    """
    Performs Caesar cipher decryption (reverse shift)
    The encryption formula from the code:
      For uppercase: ((char - 'A' + key) % 26) + 'A'
      For lowercase: ((char - 'a' + key) % 26) + 'a'
    
    To decrypt, we shift in the opposite direction (26 - key)
    """
    decrypted = []
    reverse_key = 26 - key  # Reverse shift
    
    for c in encrypted:
        if 'A' <= c <= 'Z':
            # Uppercase letter
            shifted = ((ord(c) - ord('A') + reverse_key) % 26) + ord('A')
            decrypted.append(chr(shifted))
        elif 'a' <= c <= 'z':
            # Lowercase letter
            shifted = ((ord(c) - ord('a') + reverse_key) % 26) + ord('a')
            decrypted.append(chr(shifted))
        else:
            # Non-alphabetic characters remain unchanged
            decrypted.append(c)
    
    return ''.join(decrypted)


def pad_base64(b64_string):
    """
    Adds padding to Base64 string if needed
    """
    padding = 4 - (len(b64_string) % 4)
    if padding < 4:
        return b64_string + ('=' * padding)
    return b64_string


def solve_stage2():
    """
    Solves stage2() by:
    1. Reading the encrypted string from the program
    2. Performing reverse Caesar Shift with the identified key (13)
    3. Printing the result to the console
    """
    # Get address in the current program's address space
    address_factory = currentProgram.getAddressFactory()
    string_addr = address_factory.getDefaultAddressSpace().getAddress(STAGE2_STRING_ADDR)
    
    # Read the encrypted string from memory
    encrypted_string = read_null_terminated_string(string_addr)
    print("Encrypted string at 0x{:x}: {}".format(STAGE2_STRING_ADDR, encrypted_string))
    print("Caesar key: {}".format(STAGE2_CAESAR_KEY))
    
    # Perform reverse Caesar shift
    # The code ENCRYPTS the stored string, so we need to DECRYPT to get the password
    decrypted_string = caesar_decrypt(encrypted_string, STAGE2_CAESAR_KEY)
    
    print("Decrypted password (Stage 2 solution): {}".format(decrypted_string))
    
    return decrypted_string


def solve_stage3():
    """
    Solves stage3() by:
    1. Reading the Base64 encoded string from the program
    2. Base64 decoding the string
    3. Printing the result to the console
    """
    # Get address in the current program's address space
    address_factory = currentProgram.getAddressFactory()
    string_addr = address_factory.getDefaultAddressSpace().getAddress(STAGE3_BASE64_ADDR)
    
    # Read the Base64 encoded string from memory
    base64_string = read_null_terminated_string(string_addr)
    print("Base64 string at 0x{:x}: {}".format(STAGE3_BASE64_ADDR, base64_string))
    
    # Base64 decode the string
    try:
        decoded_bytes = base64.b64decode(base64_string)
        decoded_string = decoded_bytes.decode('utf-8')
        print("Decoded password (Stage 3 solution): {}".format(decoded_string))
    except Exception as e:
        print("Error decoding Base64: {}".format(str(e)))
        # Try with padding fix
        padded_base64 = pad_base64(base64_string)
        decoded_bytes = base64.b64decode(padded_base64)
        decoded_string = decoded_bytes.decode('utf-8')
        print("Decoded password (with padding fix): {}".format(decoded_string))
    
    return decoded_string


def main():
    print("=== CTF Stage Solver ===\n")
    
    # Solve Stage 2
    print("--- Solving Stage 2 (Caesar Cipher) ---")
    stage2_solution = solve_stage2()
    
    print("")
    
    # Solve Stage 3
    print("--- Solving Stage 3 (Base64) ---")
    stage3_solution = solve_stage3()
    
    print("\n=== Done ===")
    print("\nSummary:")
    print("  Stage 2 password: {}".format(stage2_solution))
    print("  Stage 3 password: {}".format(stage3_solution))


# Run the script
if __name__ == "__main__":
    main()
else:
    # When run from Ghidra Script Manager
    main()