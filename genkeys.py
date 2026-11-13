#!/usr/bin/env python3
"""
Keygen for keygenme.exe

Author: Ryan Godburn

This script generates valid license keys for keygenme.exe by reverse engineering
the validation algorithm used by the target program.

The validation algorithm works as follows:
    1. Key must be exactly 16 characters long
    2. XOR all 16 bytes together to get XOR_result
    3. Sum all 16 bytes (treating each as a signed char: -128 to 127)
    4. Validation passes if: (XOR_result + SUM_result) & 0xFF == 216

The value 216 (0xD8) is the magic constant that the program checks against.
When interpreted as a signed byte, 216 equals -40.
"""

import random
import string


def validate_key(key):
    """
    Validate a license key according to the keygenme.exe algorithm.
    
    This function replicates the validation logic used by the target
    program to determine if a key is valid.
    
    Args:
        key (str): The license key string to validate
        
    Returns:
        bool: True if the key is valid, False otherwise
    """
    # First check: key must be exactly 16 characters
    if len(key) != 16:
        return False
    
    # Initialize accumulators for XOR and addition operations
    xor_sum = 0  # XOR all bytes together
    add_sum = 0  # Sum all bytes (as signed values)
    
    # Process each character in the key
    for char in key:
        # Get the ASCII value of the character (0-255)
        byte_val = ord(char)
        
        # XOR operation: accumulate XOR of all bytes
        xor_sum ^= byte_val
        
        # Convert unsigned byte (0-255) to signed byte (-128 to 127)
        # Values 0-127 stay the same, values 128-255 become -128 to -1
        signed_val = byte_val if byte_val < 128 else byte_val - 256
        add_sum += signed_val
    
    # Final validation check:
    # Add the XOR result and SUM result, mask to 8 bits, compare to magic value 216
    result = (xor_sum + add_sum) & 0xFF
    return result == 216


def generate_key():
    """
    Generate a valid license key using a brute-force approach.
    
    Strategy:
        1. Generate 15 random characters
        2. Try all possible characters for the 16th position
        3. Test each combination until we find one that validates
        4. Repeat if no valid key found 
                         
    Returns:
        str: A valid 16-character license key
        
    Raises:
        Exception: If unable to generate a valid key after max_attempts iterations
    """
    
    # Command line safe charset: only letters and digits
    # These characters don't require escaping or quotes in shells
    charset = string.ascii_letters + string.digits
    
    # Safety limit to prevent infinite loops
    max_attempts = 1000
    
    for _ in range(max_attempts):
        # Step 1: Generate the first 15 characters randomly
        key_chars = [random.choice(charset) for _ in range(15)]
        
        # Step 2: Try each possible character for the 16th position
        for last_char in charset:
            test_key = ''.join(key_chars) + last_char
            
            # Step 3: Test if this combination produces a valid key
            if validate_key(test_key):
                return test_key
    
    # Fallback error
    raise Exception("Failed to generate key after maximum attempts")


def main():
    """
    Main function to demonstrate key generation and validation.
    
    Generates multiple valid keys and displays them with verification status.
    All keys are generated in safe_mode for command-line compatibility.
    """
    # Display header
    print("=" * 50)
    print("KeygenMe.exe License Key Generator")
    print("Author: Ryan Godburn")
    print("=" * 50)
    print("\nGenerating keys")
    
    # Generate and display first valid key with verification
    print("1. Valid Key #1:")
    key1 = generate_key()
    print(f"   {key1}")
    
    # Generate and display second valid key with verification
    print("\n2. Valid Key #2:")
    key2 = generate_key()
    print(f"   {key2}")
    
    # Generate additional keys
    print("\n3. Additional Valid Keys:")
    for i in range(3):
        key = generate_key()
        print(f"   Key #{i+3}: {key}")
    
    # Display closing banner
    print("\n" + "=" * 50)


# Entry point: run main() if script is executed directly
if __name__ == "__main__":
    main()