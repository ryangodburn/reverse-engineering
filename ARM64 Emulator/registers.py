"""
ARM64 Registers Module
Written by: Ryan Godburn

Implements all ARM64 registers including general purpose, special registers,
and processor state flags. This module simulates the CPU register file that
stores temporary values during program execution.

ARM64 Register Architecture:
- 31 general purpose registers (X0-X30): 64-bit registers for general use
- X30 serves dual purpose as Link Register (LR) for function returns
- Zero Register (XZR): Always reads as 0, writes are ignored
- Stack Pointer (SP): Points to top of stack
- Program Counter (PC): Points to next instruction to execute
- 32-bit views (W0-W30): Lower 32 bits of X registers

Register Naming Convention:
- X prefix: 64-bit register (X0, X1, ..., X30)
- W prefix: 32-bit register (W0, W1, ..., W30) - lower half of X register
- Special: SP (stack pointer), PC (program counter), XZR/WZR (zero register)

Task 2: Implement register bank with all ARM64 registers
Task 6: Support 32-bit W registers with proper zero-extension
"""


class ARM64Registers:
    """
    ARM64 register bank implementation.
    
    This class simulates the register file inside an ARM64 CPU. Registers
    are the fastest storage locations in a processor, used for holding
    operands, results, and addresses during computation.
    
    Key Parts:
    1. General Purpose Registers: X0-X30 can hold any data
    2. Zero Register: XZR/WZR always reads 0, discards writes
    3. Register Aliasing: W registers are 32-bit views of X registers
    4. Special Registers: SP for stack, PC for instruction pointer
    5. Processor Flags: N (negative) and Z (zero) for conditionals
    
    ARM64 ABI:
    - X0-X7: Argument/result registers
    - X8: Indirect result register
    - X9-X15: Temporary registers
    - X16-X17: Intra-procedure call registers
    - X18: Platform register
    - X19-X28: Callee-saved registers
    - X29: Frame pointer (FP)
    - X30: Link register (LR)
    """
    
    def __init__(self):
        """
        Initialize all registers to zero and create register mapping.
        
        Sets up the register file with all registers cleared to 0,
        matching the state of a freshly reset processor. Also creates
        aliases for case-insensitive access.
        """
        # Main register storage dictionary
        # Using dict for O(1) access by name instead of array indexing
        self.registers = {}
        
        # Initialize 31 general purpose registers (X0-X30)
        # Each can hold a 64-bit value (8 bytes)
        for i in range(31):
            self.registers[f'X{i}'] = 0
        
        # Initialize special registers
        self.registers['XZR'] = 0  # Zero register (always reads as 0, writes ignored)
        self.registers['SP'] = 0   # Stack Pointer - points to top of stack
        self.registers['PC'] = 0   # Program Counter - current instruction address
        
        # Note: X30 is the Link Register (LR) in ARM64
        # Used to store return address when calling functions
        # We don't need a separate LR entry since X30 serves this purpose
        
        # Processor state flags 
        self.n_flag = 0  # Negative flag: 1 if last result was negative
        self.z_flag = 0  # Zero flag: 1 if last result was zero

        # Internal bookkeeping for execution tracing (Task 5)
        # Tracks register updates for debugging output
        self._update_log = []           # List of (register, value, bits) tuples
        self._logging_enabled = True     # Can disable for performance

        # Create lowercase aliases for convenience (x0 -> X0, etc.)
        self.create_aliases()
    
    def create_aliases(self):
        """
        Create lowercase aliases for all registers for case-insensitive access.
        
        This allows code to use 'x0' or 'X0' interchangeably, matching
        how assembly is often written in different styles.
        """
        # Create a snapshot of keys to avoid modifying dict during iteration
        upper_keys = list(self.registers.keys())
        for key in upper_keys:
            # Map lowercase version to same storage location
            self.registers[key.lower()] = self.registers[key]
    
    def read(self, register):
        """
        Read value from a register.
        
        Handles both 64-bit (X) and 32-bit (W) register reads with proper
        semantics. Reading from W register returns only lower 32 bits.
        
        Args:
            register (str): Register name (case-insensitive)
                          Examples: "X0", "W0", "SP", "xzr"
        
        Returns:
            int: Value stored in the register
                 For W registers, returns only lower 32 bits
        
        Raises:
            KeyError: If register name is invalid
        
        Examples:
            >>> regs = ARM64Registers()
            >>> regs.write("X0", 0x123456789ABCDEF0)
            >>> regs.read("X0")
            0x123456789ABCDEF0  # Full 64 bits
            >>> regs.read("W0")
            0x9ABCDEF0          # Lower 32 bits only
        """
        reg_name = register.upper()
        
        # Zero registers always return 0, regardless of internal state
        if reg_name == 'XZR':
            return 0
        if reg_name == 'WZR':
            return 0

        # Handle 32-bit W register reads (Task 6)
        # W registers are aliases for lower 32 bits of X registers
        if reg_name.startswith('W'):
            # Convert W0 -> X0, W1 -> X1, etc.
            x_reg = f"X{reg_name[1:]}"
            if x_reg in self.registers:
                # Mask to get only lower 32 bits
                return self.registers[x_reg] & 0xFFFFFFFF
            else:
                raise KeyError(f"Invalid register: {register}")

        # Standard 64-bit register read
        if reg_name in self.registers:
            return self.registers[reg_name]
        else:
            raise KeyError(f"Invalid register: {register}")
    
    def write(self, register, value):
        """
        Write value to a register.
        
        Handles both 64-bit and 32-bit writes with proper semantics.
        Writing to a W register zeros the upper 32 bits of the X register.
        
        Args:
            register (str): Register name (case-insensitive)
            value (int): Value to write
                        Will be masked to appropriate bit width
        
        Raises:
            KeyError: If register name is invalid
        
        Examples:
            >>> regs = ARM64Registers()
            >>> regs.write("X0", 0xFFFFFFFFFFFFFFFF)  # Write 64 bits
            >>> regs.write("W0", 0x12345678)          # Zeros upper 32 bits
            >>> regs.read("X0")
            0x12345678  # Upper 32 bits cleared by W0 write
        """
        reg_name = register.upper()
        
        # Writes to zero registers are silently discarded
        # This is hardware behavior - allows using XZR as a "sink"
        if reg_name in ['XZR', 'WZR']:
            return

        # Handle 32-bit register writes with zero-extension (Task 6)
        # Writing to W register clears upper 32 bits of X register
        if reg_name.startswith('W'):
            self.write_32bit_register(reg_name, value)
            return

        # Ensure value fits in 64 bits (prevent overflow)
        # Python ints are unlimited, but registers are 64-bit
        value = value & 0xFFFFFFFFFFFFFFFF

        if reg_name in self.registers:
            # Update the register value
            self.registers[reg_name] = value
            # Keep lowercase alias in sync
            self.registers[reg_name.lower()] = value
            # Log the update for tracing
            self.record_update(reg_name, value, 64)
        else:
            raise KeyError(f"Invalid register: {register}")

    def write_32bit_register(self, reg_name: str, value: int) -> None:
        """
        Helper to write to a 32-bit W register with zero extension.
        
        When writing to a W register, ARM64 architecture specifies that
        the upper 32 bits of the corresponding X register are cleared.
        
        Args:
            reg_name: W register name (e.g., "W0", "W5")
            value: Value to write (will be masked to 32 bits)
        """
        # Map W register to corresponding X register
        x_reg = f"X{reg_name[1:]}"
        if x_reg not in self.registers:
            raise KeyError(f"Invalid register: {reg_name}")

        # Mask value to 32 bits 
        value = value & 0xFFFFFFFF

        # Write to X register (automatically zero-extends)
        self.registers[x_reg] = value
        self.registers[x_reg.lower()] = value

        # Log both W and X register updates
        self.record_update(reg_name, value, 32)
        self.record_update(x_reg, value, 64)
    
    def update_flags(self, result, is_64bit=True):
        """
        Update processor state flags based on operation result.
        
        ARM64 has NZCV flags that are set by arithmetic operations:
        - N (Negative): Set if result is negative (MSB = 1)
        - Z (Zero): Set if result is zero
        - C (Carry): Set if unsigned overflow (not implemented)
        - V (overflow): Set if signed overflow (not implemented)
        
        These flags are used by conditional branches (b.eq, b.ne, etc.)
        
        Args:
            result (int): Result of the arithmetic operation
            is_64bit (bool): Whether this was a 64-bit operation
                           Determines which bit is the sign bit
        """
        # Mask result to appropriate size
        if is_64bit:
            result = result & 0xFFFFFFFFFFFFFFFF
            # Check if negative: bit 63 (MSB) set in 64-bit value
            # In two's complement, MSB = 1 means negative
            self.n_flag = 1 if (result & (1 << 63)) else 0
        else:
            result = result & 0xFFFFFFFF
            # Check if negative: bit 31 (MSB) set in 32-bit value
            self.n_flag = 1 if (result & (1 << 31)) else 0
        
        # Set zero flag if result is exactly zero
        self.z_flag = 1 if result == 0 else 0
    
    def get_pc(self):
        """
        Get the current program counter value.
        
        The PC points to the next instruction to be executed.
        In ARM64, PC increments by 4 after each instruction.
        """
        return self.registers['PC']
    
    def set_pc(self, value):
        """
        Set the program counter value.
        
        Used for branches and jumps to change control flow.
        """
        self.write('PC', value)
    
    def increment_pc(self, amount=4):
        """
        Increment the program counter.
        
        Called after executing each instruction to advance to the next.
        ARM64 instructions are always 32 bits (4 bytes), so we increment
        by 4.
        
        Args:
            amount (int): Amount to increment (default 4 for 32-bit instruction)
        """
        self.registers['PC'] = (self.registers['PC'] + amount) & 0xFFFFFFFFFFFFFFFF
        self.registers['pc'] = self.registers['PC']  # Keep alias in sync
    
    def get_sp(self):
        """
        Get the current stack pointer value.
        
        SP points to the top of the stack (lowest used address).
        Stack grows downward in ARM64.
        """
        return self.registers['SP']
    
    def set_sp(self, value):
        """
        Set the stack pointer value.
        
        Modified by PUSH/POP operations and stack frame setup.
        """
        self.write('SP', value)
    
    def reset(self):
        """
        Reset all registers to zero.
        
        Returns the register bank to initial state, like a CPU reset.
        Used when starting execution of a new program.
        """
        # Temporarily disable logging during reset
        previous_logging = self._logging_enabled
        self._logging_enabled = False

        # Clear all registers to 0
        for key in self.registers:
            self.registers[key] = 0

        # Restore logging state and clear logs
        self._logging_enabled = previous_logging
        self.clear_update_log()
        
        # Clear processor flags
        self.n_flag = 0
        self.z_flag = 0

    def clear_update_log(self):
        """Clear the register update log used for execution tracing."""
        self._update_log = []

    def consume_update_log(self):
        """
        Return and clear the current update log.
        
        Used by the emulator to get register changes for trace output.
        """
        updates = list(self._update_log)
        self._update_log = []
        return updates

    def record_update(self, register, value, bits):
        """
        Record a register write for execution tracing.
        
        Maintains a log of register changes for debugging output.
        Only keeps the latest update for each register.
        """
        if not self._logging_enabled:
            return

        canonical = register.upper()

        # Skip logging PC updates (reported separately in trace)
        if canonical == 'PC':
            return

        # Create update entry
        entry = (canonical, value & ((1 << bits) - 1) if bits < 64 else value, bits)

        # Replace existing entry for this register or append new
        for index, (name, _, _) in enumerate(self._update_log):
            if name == canonical:
                self._update_log[index] = entry
                break
        else:
            self._update_log.append(entry)
    
    def display(self):
        """
        Display all registers in a formatted output.
        
        Shows registers in three columns for readability, displaying
        all general purpose registers plus special registers and flags.
        Format matches common debugger output.
        """
        print("-" * 125)
        print("Registers:")
        print("-" * 125)
        
        # Display general purpose registers in three columns
        # Column 1: X0-X9, Column 2: X10-X19, Column 3: X20-X29
        for i in range(10):
            # Column 1: X0-X9
            reg1 = f"X{i}"
            val1 = self.registers[reg1.upper()]
            
            # Column 2: X10-X19
            reg2 = f"X{i+10}"
            val2 = self.registers[reg2.upper()]
            
            # Column 3: X20-X29
            reg3 = f"X{i+20}"
            val3 = self.registers[reg3.upper()]
            
            # Print with aligned columns (16 hex digits for 64-bit values)
            print(f"{reg1:3}: 0x{val1:016x}  "
                  f"{reg2:3}: 0x{val2:016x}  "
                  f"{reg3:3}: 0x{val3:016x}")
        
        # Display special registers on last line
        sp_val = self.registers['SP']
        pc_val = self.registers['PC']
        x30_val = self.registers['X30']  # Link Register
        
        print(f"SP : 0x{sp_val:016x}  "
              f"PC : 0x{pc_val:016x}  "
              f"X30: 0x{x30_val:016x}")
        
        # Display processor state flags
        print(f"\nProcessor State N bit: {self.n_flag}")
        print(f"Processor State Z bit: {self.z_flag}")
        print()
    
    def __str__(self):
        """String representation showing key register values."""
        return (f"PC=0x{self.registers['PC']:016x}, "
                f"SP=0x{self.registers['SP']:016x}, "
                f"X0=0x{self.registers['X0']:016x}, "
                f"N={self.n_flag}, Z={self.z_flag}")
    
    def __repr__(self):
        """Detailed representation for debugging."""
        return f"ARM64Registers({self.__str__()})"