"""
ARM64 Memory Module
Written by: Ryan Godburn

Implements stack memory for the ARM64 emulator, simulating how a real ARM64
processor interacts with RAM. This module provides a 256-byte memory space
that acts as the program stack, supporting both individual byte operations
and multi-byte reads/writes for different data sizes.

Key Features:
- 256 bytes of contiguous memory
- Little-endian byte ordering (matches ARM64 architecture)
- Support for 8-bit (byte), 32-bit (word), and 64-bit (doubleword) operations
- Memory-mapped at high address (0x7FFFFF00)
- Hexdump visualization for debugging memory contents

Task 3: Prepare stack memory (256 bytes).

Memory Layout:
    Base Address (0x7FFFFF00) -> [   Stack grows downward   ] <- SP initial
    Higher addresses are at the "bottom" of the stack in ARM64
"""

import struct


class ARM64Memory:
    """
    Stack memory implementation for ARM64 emulator.
    
    The memory is byte-addressable, meaning each address points to a single
    byte, but we support multi-byte operations for efficiency when working
    with 32-bit and 64-bit values.
    
    Attributes:
        size: Total bytes of memory available (default 256)
        base_address: Starting address in the virtual address space
        memory: The actual byte storage (bytearray for mutability)
        reads/writes: Statistics counters for debugging
    """
    
    def __init__(self, size=256, base_address=0x0):
        """
        Initialize stack memory.
        
        Creates a block of memory that can be accessed via addresses.
        The base_address parameter allows this memory to be "placed"
        anywhere in the virtual address space.
        
        Args:
            size (int): Size of stack in bytes (default 256)
                       256 bytes = 32 quadwords = typical small stack
            base_address (int): Base address of stack (default 0x0)
                              Usually set high (e.g., 0x7FFFFF00)
        """
        # Store configuration
        self.size = size
        self.base_address = base_address
        
        # Initialize memory as a bytearray for efficient byte operations
        # bytearray is mutable (unlike bytes) and provides direct indexing
        # All bytes start at 0 (cleared memory)
        self.memory = bytearray(size)
        
        # Statistics for debugging
        self.reads = 0   # Count of read operations
        self.writes = 0  # Count of write operations
    
    def read_byte(self, address):
        """
        Read a single byte from memory.
        
        This is the fundamental memory read operation. All other read
        operations are built on top of this. Simulates how a CPU would
        fetch a single byte from RAM.
        
        Args:
            address (int): Absolute memory address to read from
                         Must be within [base_address, base_address+size)
            
        Returns:
            int: Byte value at the address (0-255)
            
        Raises:
            MemoryError: If address is out of bounds (segmentation fault)
        
        Example:
            >>> mem = ARM64Memory(size=256, base_address=0x1000)
            >>> mem.write_byte(0x1000, 0x42)
            >>> mem.read_byte(0x1000)
            66  # (0x42 in decimal)
        """
        # Convert absolute address to offset within our memory block
        # For example, if base=0x1000 and address=0x1005, offset=5
        offset = address - self.base_address
        
        # Bounds checking - simulate memory protection
        # In real systems, accessing invalid memory causes segmentation faults
        if offset < 0 or offset >= self.size:
            raise MemoryError(f"Memory access out of bounds: 0x{address:x} "
                            f"(valid range: 0x{self.base_address:x}-"
                            f"0x{self.base_address + self.size - 1:x})")
        
        # Track statistics for performance analysis
        self.reads += 1
        
        # Return the byte value at this offset
        return self.memory[offset]
    
    def write_byte(self, address, value):
        """
        Write a single byte to memory.
        
        Fundamental write operation that stores one byte at a specific
        address. 
        
        Args:
            address (int): Memory address to write to
                         Must be within valid range
            value (int): Byte value to write (0-255)
                        Values outside this range are invalid
            
        Raises:
            MemoryError: If address is out of bounds
            ValueError: If value is not a valid byte (0-255)
        
        Example:
            >>> mem = ARM64Memory(size=256, base_address=0x1000)
            >>> mem.write_byte(0x1000, 0xFF)  # Write 255
            >>> mem.write_byte(0x1001, 0x00)  # Write 0
        """
        # Convert absolute address to offset
        offset = address - self.base_address
        
        # Bounds checking for memory safety
        if offset < 0 or offset >= self.size:
            raise MemoryError(f"Memory access out of bounds: 0x{address:x} "
                            f"(valid range: 0x{self.base_address:x}-"
                            f"0x{self.base_address + self.size - 1:x})")
        
        # Ensure value is a valid byte (8 bits = 0-255)
        if not 0 <= value <= 255:
            raise ValueError(f"Invalid byte value: {value} (must be 0-255)")
        
        # Store the byte and update statistics
        self.memory[offset] = value
        self.writes += 1
    
    def read(self, address, size=8):
        """
        Read multiple bytes from memory as a single integer value.
        
        This method reads 'size' consecutive bytes starting at 'address'
        and combines them into a single integer using little-endian byte
        ordering (least significant byte first).
        
        Args:
            address (int): Starting memory address
            size (int): Number of bytes to read (default 8 for 64-bit)
                       Common values: 1 (byte), 4 (32-bit), 8 (64-bit)
            
        Returns:
            int: Combined value from the bytes (little-endian)
        
        Example:
            If memory contains: [0x78, 0x56, 0x34, 0x12] at address
            read(address, 4) returns 0x12345678 (little-endian)
        """
        # Read bytes one at a time to leverage bounds checking
        bytes_read = []
        for i in range(size):
            bytes_read.append(self.read_byte(address + i))
        
        # Convert bytes to integer using little-endian ordering
        # In little-endian: first byte is least significant
        # Example: [0x78, 0x56, 0x34, 0x12] becomes:
        #   0x78 << 0  = 0x00000078
        #   0x56 << 8  = 0x00005600
        #   0x34 << 16 = 0x00340000
        #   0x12 << 24 = 0x12000000
        #   Total:       0x12345678
        value = 0
        for i, byte_val in enumerate(bytes_read):
            value |= byte_val << (i * 8)
        
        return value
    
    def write(self, address, value, size=8):
        """
        Write multiple bytes to memory from a single integer value.
        
        Stores an integer value as 'size' consecutive bytes using
        little-endian byte ordering. 
        
        Args:
            address (int): Starting memory address
            value (int): Value to write (will be split into bytes)
            size (int): Number of bytes to write (default 8 for 64-bit)
        
        Example:
            write(address, 0x12345678, 4) stores:
            [0x78, 0x56, 0x34, 0x12] in little-endian order
        """
        # Convert value to bytes using little-endian ordering
        # Extract each byte by shifting and masking
        for i in range(size):
            # Extract byte i: shift right by i*8 bits, mask to get lowest byte
            byte_val = (value >> (i * 8)) & 0xFF
            self.write_byte(address + i, byte_val)
    
    def read_64(self, address):
        """
        Read a 64-bit value from memory (little-endian).
        
        Convenience method for reading 8 bytes as a 64-bit integer.
        Used for loading X registers and 64-bit data.
        """
        return self.read(address, 8)
    
    def write_64(self, address, value):
        """
        Write a 64-bit value to memory (little-endian).
        
        Convenience method for storing 8 bytes from a 64-bit integer.
        Used for storing X register values and 64-bit data.
        """
        self.write(address, value, 8)
    
    def read_32(self, address):
        """
        Read a 32-bit value from memory (little-endian).
        
        Convenience method for reading 4 bytes as a 32-bit integer.
        Used for loading W registers and 32-bit data.
        """
        return self.read(address, 4)
    
    def write_32(self, address, value):
        """
        Write a 32-bit value to memory (little-endian).
        
        Convenience method for storing 4 bytes from a 32-bit integer.
        Used for storing W register values and 32-bit data.
        """
        self.write(address, value, 4)
    
    def clear(self):
        """
        Clear all memory to zeros.
        
        Resets the memory to initial state (all zeros) and clears
        access statistics. Simulates memory initialization.
        """
        self.memory = bytearray(self.size)
        self.reads = 0
        self.writes = 0
    
    def display(self, start_offset=0, length=None):
        """
        Display memory contents in hexdump format.
        
        Shows memory contents in a human-readable format.
        
        Format:
            address  hex_bytes  ascii_representation
            00001000  48 65 6c 6c 6f 20 57 6f  72 6c 64 00 00 00 00 00  |Hello World.....|
        
        Args:
            start_offset (int): Starting offset to display (default 0)
            length (int): Number of bytes to display (default all)
        """
        if length is None:
            length = self.size
        
        # Ensure we don't go past memory bounds
        length = min(length, self.size - start_offset)
        
        # Header with visual separator
        print("-" * 125 + "Stack:")
        print("-" * 125)
        
        # Display 16 bytes per line (standard hexdump width)
        bytes_per_line = 16
        
        for line_start in range(start_offset, start_offset + length, bytes_per_line):
            # Calculate how many bytes to display on this line
            # (last line might have fewer than 16)
            line_length = min(bytes_per_line, (start_offset + length) - line_start)
            
            # Print address column (8 hex digits for 32-bit address)
            addr = self.base_address + line_start
            print(f"{addr:08x}  ", end="")
            
            # Build hex and ASCII strings for this line
            hex_str = ""
            ascii_str = ""
            
            for i in range(bytes_per_line):
                if i < line_length:
                    # Get the byte value
                    byte_val = self.memory[line_start + i]
                    hex_str += f"{byte_val:02x} "
                    
                    # Build ASCII representation
                    # Only show printable ASCII characters (32-126)
                    # Non-printable characters shown as dots
                    if 32 <= byte_val <= 126:  # Printable ASCII range
                        ascii_str += chr(byte_val)
                    else:
                        ascii_str += "."
                else:
                    # Padding for incomplete lines (last line)
                    hex_str += "   "
                    
                # Add extra space in the middle for readability
                # Separates the line into two 8-byte groups
                if i == 7:
                    hex_str += " "
            
            # Print the complete line with ASCII sidebar
            print(f"{hex_str} |{ascii_str}|")
        
        # Print final address (showing end of displayed memory)
        end_addr = self.base_address + start_offset + length
        print(f"{end_addr:08x}")
        print()
    
    def get_statistics(self):
        """
        Get memory access statistics.
        
        Returns detailed statistics about memory usage.
        
        Returns:
            dict: Statistics including:
                - size: Total memory size
                - base_address: Starting address (hex)
                - end_address: Last valid address (hex)
                - reads: Number of read operations
                - writes: Number of write operations
                - bytes_modified: Count of non-zero bytes
        """
        return {
            'size': self.size,
            'base_address': f"0x{self.base_address:x}",
            'end_address': f"0x{self.base_address + self.size - 1:x}",
            'reads': self.reads,
            'writes': self.writes,
            'bytes_modified': sum(1 for b in self.memory if b != 0)
        }
    
    def __str__(self):
        """
        String representation showing memory info.
        
        Provides a concise summary of the memory state.
        """
        stats = self.get_statistics()
        return (f"ARM64Memory(size={stats['size']}, "
                f"base={stats['base_address']}, "
                f"reads={stats['reads']}, "
                f"writes={stats['writes']})")
    
    def __repr__(self):
        """
        Detailed representation for debugging.
        
        Returns the same as __str__ for consistent representation.
        """
        return self.__str__()