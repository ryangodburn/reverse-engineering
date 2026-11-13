"""
Instruction Module
Written by: Arjun Aravind

Defines the Instruction class and instruction-specific parsing logic. This module
handles the conversion of text-based assembly instructions into structured objects
that can be analyzed and executed.

Each Instruction object represents a single ARM64 machine instruction with:
- Address: Memory location where instruction resides
- Machine code: 32-bit encoded instruction (8 hex digits)
- Mnemonic: Instruction name (add, sub, mov, etc.)
- Operands: Arguments to the instruction (registers, immediates, memory)
- Metadata: Structured information for execution
"""

import re
from utils import parse_operand


class Instruction:
    """
    Represents a single ARM64 instruction with its components.
    
    This class encapsulates all information about an instruction:
    - Location in memory (address)
    - Binary encoding (machine code)
    - Human-readable form (mnemonic and operands)
    - Parsed structure (for execution)
    
    ARM64 instructions have various formats:
    - R-type: Register operations (add x0, x1, x2)
    - I-type: Immediate operations (add x0, x1, #10)
    - Load/Store: Memory access (ldr x0, [sp, #8])
    - Branch: Control flow (b 0x40, b.eq label)
    """
    
    def __init__(self, address, machine_code, instruction_text):
        """
        Initialize an instruction.
        
        Creates an instruction object with raw data that will be
        parsed to extract the mnemonic and operands.
        
        Args:
            address (str): Memory address of the instruction (hex string)
                         Example: "0", "4", "8", "c"
            machine_code (str): Machine code representation (32-bit hex)
                              Example: "d10043ff" for sub sp, sp, #0x10
            instruction_text (str): The assembly instruction text
                                  Example: "sub sp, sp, #0x10"
        """
        self.address = address              # Instruction address (as string)
        self.machine_code = machine_code    # 32-bit encoded instruction
        self.instruction_text = instruction_text  # Original assembly text
        self.mnemonic = ""                  # Instruction name (add, sub, etc.)
        self.operands = []                  # List of operand strings
        self.operand_values = []            # Raw operand values for branches
        self.pc_value = 0                   # PC value for this instruction (Task 4)
        self.metadata = {}                  # Structured data for execution (Task 5)
    
    def parse(self):
        """
        Parse the instruction text to extract mnemonic and operands.
        
        Splits the instruction into its mnemonic (operation name) and
        operands (arguments), then delegates to specific parsing logic
        based on the instruction type.
        
        Process:
        1. Split text into mnemonic and operand string
        2. Identify instruction type
        3. Call appropriate operand parser
        4. Store parsed results
        """
        # Split instruction text into mnemonic and operands
        # Example: "sub sp, sp, #0x10" -> ["sub", "sp, sp, #0x10"]
        parts = self.instruction_text.strip().split(None, 1)
        
        if not parts:
            return  # Empty instruction
        
        # First part is the mnemonic (instruction name)
        # Convert to lowercase for consistent handling
        self.mnemonic = parts[0].lower()
        
        # Parse operands if they exist
        if len(parts) > 1:
            self.parse_operands(parts[1])
    
    def parse_operands(self, operands_str):
        """
        Parse the operands string based on instruction type.
        
        Args:
            operands_str (str): String containing all operands
                              Example: "x0, x1, #10" or "[sp, #8]"
        
        Instruction categories:
        - Data processing: 3 operands (dest, src1, src2)
        - Move: 2 operands (dest, source)
        - Load/Store: Register and memory address
        - Branch: Target address or label
        - Compare: 2 operands to compare
        - Special: RET, NOP (no operands)
        """
        # Map of instruction types to their parsing methods
        # This allows us to handle different operand formats correctly
        instruction_parsers = {
            # Data processing instructions (3 register operands)
            # Format: Rd, Rn, Rm or Rd, Rn, #immediate
            'add': self.parse_three_register,   # Addition
            'sub': self.parse_three_register,   # Subtraction
            'and': self.parse_three_register,   # Bitwise AND
            'eor': self.parse_three_register,   # Exclusive OR
            'mul': self.parse_three_register,   # Multiplication
            
            # Move instruction
            # Format: Rd, Rm or Rd, #immediate
            'mov': self.parse_mov,
            
            # Load/Store instructions
            # Format: Rt, [Rn] or Rt, [Rn, #offset]
            'ldr': self.parse_load_store,       # Load register
            'ldrb': self.parse_load_store,      # Load byte
            'str': self.parse_load_store,       # Store register
            'strb': self.parse_load_store,      # Store byte
            
            # Branch instructions
            # Format: target or target <label>
            'b': self.parse_branch,             # Unconditional branch
            'b.gt': self.parse_branch,          # Branch if greater
            'b.le': self.parse_branch,          # Branch if less/equal
            'b.eq': self.parse_branch,          # Branch if equal
            'b.ne': self.parse_branch,          # Branch if not equal
            
            # Compare instruction
            # Format: Rn, Rm or Rn, #immediate
            'cmp': self.parse_cmp,
            
            # Instructions with no operands
            'ret': self.parse_no_operands,      # Return
            'nop': self.parse_no_operands       # No operation
        }
        
        # Get the appropriate parser for this instruction
        # Default to generic parser for unknown instructions
        parser_func = instruction_parsers.get(self.mnemonic, self.parse_generic)
        parser_func(operands_str)
    
    def parse_three_register(self, operands_str):
        """
        Parse instructions with three register operands.
        
        These are typically arithmetic and logical operations that
        perform: destination = source1 OP source2
        
        Format: Rd, Rn, Rm or Rd, Rn, #imm
        Example: add x0, x1, x2  -> x0 = x1 + x2
                sub sp, sp, #16  -> sp = sp - 16
        
        Args:
            operands_str: String like "x0, x1, x2" or "sp, sp, #0x10"
        """
        # Split by comma and clean up whitespace
        parts = [p.strip() for p in operands_str.split(',')]
        
        if len(parts) == 3:
            self.operands = [
                parse_operand(parts[0]),  # Destination register (Rd)
                parse_operand(parts[1]),  # Source register 1 (Rn)
                parse_operand(parts[2])   # Source register 2 (Rm) or immediate
            ]
    
    def parse_mov(self, operands_str):
        """
        Parse MOV instruction.
        
        MOV copies a value from source to destination.
        Can move from register to register or immediate to register.
        
        Format: Rd, #imm or Rd, Rm
        Example: mov x0, #42     -> x0 = 42
                mov x1, x0      -> x1 = x0
        
        Args:
            operands_str: String like "x0, #42" or "x0, x1"
        """
        # Split into destination and source
        parts = [p.strip() for p in operands_str.split(',', 1)]
        
        if len(parts) == 2:
            dest = parse_operand(parts[0])
            
            # Check if source has a comment and remove it
            src = parts[1].strip()
            if '//' in src:
                # Extract just the value before the comment
                # Example: "#0x10 // some comment" -> "#0x10"
                src = src.split('//')[0].strip()
            
            self.operands = [dest, parse_operand(src)]
    
    def parse_load_store(self, operands_str):
        """
        Parse load/store instructions.
        
        These instructions access memory, either loading from memory
        to a register or storing from a register to memory.
        
        Format: Rt, [Rn, #offset] or Rt, [Rn]
        Example: ldr x0, [sp, #8]   -> x0 = memory[sp + 8]
                str x1, [sp]       -> memory[sp] = x1
        
        The memory address is calculated as base + offset.
        
        Args:
            operands_str: String like "x0, [sp, #8]" or "x0, [sp]"
        """
        # First, separate the register from the memory operand
        # Pattern: register, [memory_address]
        match = re.match(r'([^,]+),\s*(.+)', operands_str)

        if match:
            # Extract register operand
            reg = parse_operand(match.group(1).strip())
            mem_op = match.group(2).strip()

            # Remove any trailing comments
            if '//' in mem_op:
                mem_op = mem_op.split('//')[0].strip()

            # Parse memory operand if it's in bracket notation
            if '[' in mem_op and ']' in mem_op:
                # Extract content within brackets
                start = mem_op.index('[')
                end = mem_op.index(']') + 1
                bracket_content = mem_op[start:end]

                # Default display format
                display_operand = bracket_content
                
                # Parse what's inside the brackets
                inside = bracket_content[1:-1].strip()
                base = None      # Base register
                offset = None    # Offset (register or immediate)

                if inside:
                    # Split by comma to get base and offset
                    parts = [parse_operand(p.strip()) for p in inside.split(',') if p.strip()]
                    if parts:
                        base = parts[0]      # Base register (e.g., SP)
                    if len(parts) > 1:
                        offset = parts[1]    # Offset (e.g., #8 or X1)

                    # Format display string to show computation
                    if base is not None and offset is not None:
                        display_operand = f"[{base}, {offset}] --> {base} + {offset}"
                    elif base is not None:
                        display_operand = f"[{base}]"

                # Store operands for display
                self.operands = [reg, display_operand]
                
                # Store structured metadata for execution
                self.metadata['memory'] = {
                    'base': base,        # Base register name
                    'offset': offset,    # Offset value or register
                    'raw': bracket_content,  # Original text
                    'text': mem_op       # Full memory operand
                }
            else:
                # Not a standard memory operand
                self.operands = [reg, mem_op]

    def parse_branch(self, operands_str):
        """
        Parse branch instructions.
        
        Branches change the flow of execution by modifying the PC.
        They can be unconditional (b) or conditional (b.eq, b.gt).
        
        Format: target or target <label>
        Example: b 2c              -> PC = 0x2c
                b 2c <main+0x2c>  -> PC = 0x2c (with label)
        
        The target is typically a hex address. Labels provide
        human-readable context but aren't used for execution.
        
        Args:
            operands_str: String like "2c" or "2c <main+0x2c>"
        """
        operand = operands_str.strip()

        # Remove any comments
        if '//' in operand:
            operand = operand.split('//')[0].strip()
        
        # Check if it contains a label in angle brackets
        if '<' in operand and '>' in operand:
            # Split into address and label parts
            # Format: "2c <main+0x2c>"
            parts = operand.split(None, 1)
            if len(parts) == 2:
                # Store both the hex address and the label
                self.operands = [parts[0], parts[1]]  # ["2c", "<main+0x2c>"]
            else:
                self.operands = [operand]
        else:
            # Just a hex address without label
            self.operands = [operand]

        # Parse and store branch target information
        target_str = self.operands[0] if self.operands else None
        branch_info = {'raw': operand}

        # Try to parse target address
        if target_str:
            try:
                # Convert hex string to integer
                branch_info['target'] = int(target_str, 16)
            except ValueError:
                branch_info['target'] = None  # Invalid format

        # Store label if present
        if len(self.operands) > 1:
            branch_info['label'] = self.operands[1]

        # Store structured branch data for execution
        self.metadata['branch'] = branch_info
    
    def parse_cmp(self, operands_str):
        """
        Parse CMP instruction.
        
        CMP compares two values by subtracting them and setting flags.
        The result is not stored; only flags are updated for conditionals.
        
        Format: Rn, Rm or Rn, #imm
        Example: cmp x0, #10    -> Compare x0 with 10
                cmp x1, x2     -> Compare x1 with x2
        
        Args:
            operands_str: String like "x0, #10" or "x0, x1"
        """
        # Split into two operands to compare
        parts = [p.strip() for p in operands_str.split(',')]
        
        if len(parts) == 2:
            self.operands = [
                parse_operand(parts[0]),  # First value
                parse_operand(parts[1])   # Second value
            ]
    
    def parse_no_operands(self, operands_str):
        """
        Parse instructions with no operands (RET, NOP).
        
        These instructions don't take any arguments:
        - RET: Return from function (PC = X30)
        - NOP: No operation (does nothing)
        
        Args:
            operands_str: Should be empty or whitespace
        """
        # No operands to parse
        self.operands = []
    
    def parse_generic(self, operands_str):
        """
        Generic operand parser for unrecognized instructions.
        
        Falls back to simple comma-separated parsing for instructions
        that don't have specialized handlers. This ensures we can
        at least display unknown instructions.
        
        Args:
            operands_str: String containing operands
        """
        if operands_str.strip():
            # Split by comma and parse each operand
            self.operands = [parse_operand(p.strip()) 
                           for p in operands_str.split(',')]