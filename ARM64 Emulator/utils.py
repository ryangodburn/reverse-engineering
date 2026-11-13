"""
Utility Module
Written by: Arjun Aravind

Contains helper functions for parsing ARM64 assembly. These utilities provide
common functionality needed across the parser, instruction, and emulator modules
for handling operands, registers, and immediate values.

Key Functions:
- Operand identification (register vs immediate vs memory)
- Value parsing (hex and decimal immediates)
- Register classification (X vs W, general vs special)
- Formatting utilities for display

These utilities abstract the details of ARM64 syntax and provide a clean
interface for working with assembly language constructs.
"""

import re


def parse_operand(operand):
    """
    Parse and clean up an operand.
    
    Removes extraneous whitespace and comments from an operand string,
    returning a clean version ready for further processing.
    
    Args:
        operand (str): Raw operand string from instruction text
                      May contain trailing spaces or comments
    
    Returns:
        str: Cleaned operand string
    
    Examples:
        >>> parse_operand("  x0  ")
        "x0"
        >>> parse_operand("#0x10 // stack size")
        "#0x10"
        >>> parse_operand("sp")
        "sp"
    """
    operand = operand.strip()
    
    # Remove any trailing comments after //
    # Comments provide documentation but aren't part of the operand
    if '//' in operand:
        operand = operand.split('//')[0].strip()
    
    return operand


def is_register(operand):
    """
    Check if an operand is a register.
    
    ARM64 has several types of registers:
    - General purpose 64-bit: X0-X30 (31 registers)
    - General purpose 32-bit: W0-W30 (lower halves of X registers)
    - Zero registers: XZR (64-bit), WZR (32-bit) - always read as 0
    - Stack pointer: SP (64-bit)
    - Program counter: PC (64-bit)
    
    Note: X30 serves as the Link Register (LR) for function returns
    
    Args:
        operand (str): Operand to check
    
    Returns:
        bool: True if operand is a valid register name
    
    Examples:
        >>> is_register("X0")
        True
        >>> is_register("W15")
        True
        >>> is_register("SP")
        True
        >>> is_register("X31")  # Invalid - only X0-X30
        False
        >>> is_register("#10")
        False
    """
    operand = operand.upper()
    
    # Check for 64-bit general purpose registers (X0-X30)
    # Pattern: X followed by 0-30
    # - Single digit: 0-9
    # - Teens: 10-19
    # - Twenties: 20-29
    # - Thirty: 30
    if re.match(r'^X([0-9]|[12][0-9]|30)$', operand):
        return True
    
    # Check for 32-bit general purpose registers (W0-W30)
    # These are aliases for the lower 32 bits of X registers
    if re.match(r'^W([0-9]|[12][0-9]|30)$', operand):
        return True
    
    # Check for special registers
    # XZR/WZR: Zero registers (always read 0, writes discarded)
    # SP: Stack pointer (points to top of stack)
    # PC: Program counter (current instruction address)
    if operand in ['XZR', 'WZR', 'SP', 'PC']:
        return True
    
    return False


def is_immediate(operand):
    """
    Check if an operand is an immediate value.
    
    Immediate values are constants embedded in the instruction.
    They must start with '#' and can be:
    - Decimal: #123, #-45
    - Hexadecimal: #0x7b, #0xFF
    - Negative hex: #-0x10
    
    ARM64 immediates are limited in size depending on the instruction,
    but this function just checks syntax, not value ranges.
    
    Args:
        operand (str): Operand to check
    
    Returns:
        bool: True if operand is an immediate value
    
    Examples:
        >>> is_immediate("#10")
        True
        >>> is_immediate("#0xFF")
        True
        >>> is_immediate("#-16")
        True
        >>> is_immediate("10") 
        False
        >>> is_immediate("X0")
        False
    """
    if not operand.startswith('#'):
        return False  # Immediates must start with #
    
    # Remove the # and check if it's a valid number
    value = operand[1:]
    
    try:
        # int() with base 0 automatically handles:
        # - Decimal: "123", "-45"
        # - Hexadecimal: "0x7b", "0xFF"
        # - Octal: "0o77"
        # - Binary: "0b1010"
        # - Leading +/- signs: "+10", "-0x10"
        int(value, 0)
        return True
    except ValueError:
        return False  # Not a valid number format


def parse_immediate_value(immediate):
    """
    Parse an immediate value to its integer representation.
    
    Converts an immediate value string (with # prefix) to an integer.
    Handles decimal, hexadecimal, and negative values.
    
    Args:
        immediate (str): Immediate value string (e.g., #0x10, #123, #-5)
    
    Returns:
        int: The integer value, or None if invalid format
    
    Examples:
        >>> parse_immediate_value("#10")
        10
        >>> parse_immediate_value("#0xFF")
        255
        >>> parse_immediate_value("#-16")
        -16
        >>> parse_immediate_value("#0x10")
        16
        >>> parse_immediate_value("10")
        None
        >>> parse_immediate_value("#invalid")
        None
    """
    if not immediate.startswith('#'):
        return None  # Not an immediate value
    
    # Remove the # prefix
    value_str = immediate[1:]
    
    try:
        # Parse with base 0 for automatic format detection
        # Handles decimal, hex (0x), octal (0o), binary (0b)
        return int(value_str, 0)
    except ValueError:
        return None  # Invalid number format


def get_register_size(register):
    """
    Get the size of a register in bits.
    
    Determines whether a register is 32-bit or 64-bit based on its name.
    This is important for:
    - Determining operation width (32 vs 64-bit arithmetic)
    - Proper masking of results
    - Zero-extension behavior for W registers
    
    ARM64 Register Sizes:
    - X registers: 64 bits (X0-X30, XZR)
    - W registers: 32 bits (W0-W30, WZR)
    - SP: 64 bits (stack pointer)
    - PC: 64 bits (program counter)
    
    When writing to a W register, the upper 32 bits of the
    corresponding X register are cleared (zero-extended).
    
    Args:
        register (str): Register name
    
    Returns:
        int: 64 for X registers and special registers
             32 for W registers
             64 as default for unknown registers
    
    Examples:
        >>> get_register_size("X0")
        64
        >>> get_register_size("W5")
        32
        >>> get_register_size("SP")
        64
        >>> get_register_size("w10")  # Case insensitive
        32
    """
    register = register.upper()
    
    # 64-bit registers
    if register.startswith('X') or register in ['SP', 'PC', 'XZR']:
        return 64
    
    # 32-bit registers (W registers)
    elif register.startswith('W') or register == 'WZR':
        return 32
    
    # Default to 64-bit for unknown registers
    return 64

