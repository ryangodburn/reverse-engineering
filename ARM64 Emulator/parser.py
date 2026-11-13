"""
ARM64 Parser Module
Written by: Arjun Aravind

Responsible for reading and parsing ARM64 assembly instructions from file.
The parser converts human-readable assembly code into structured instruction
objects that can be analyzed or executed by the emulator.

Key Functions:
- Read assembly files line by line
- Extract instruction components (address, opcode, mnemonic, operands)
- Track Program Counter (PC) progression through code
- Build instruction list for execution

Task 1: Initial parser implementation
Task 4: Updates PC during parsing to track instruction addresses

Input Format:
    address: machine_code    mnemonic operands    ; comments
    Example: 0: d10043ff    sub sp, sp, #0x10   ; allocate stack frame
"""

from instruction import Instruction
from registers import ARM64Registers
from memory import ARM64Memory


class ARM64Parser:
    """
    Parser for ARM64 assembly instructions.
    
    This class reads ARM64 assembly code from a file and converts it into
    a list of Instruction objects. It simulates how an assembler would
    process assembly language, tracking addresses and parsing mnemonics
    with their operands.
    
    The parser also maintains its own register bank and memory to support
    future execution, though these remain unmodified during parsing.
    
    Attributes:
        instructions: List of parsed Instruction objects
        line_number: Current line being processed
        registers: Register bank (for PC tracking)
        memory: Stack memory (initialized but not used during parsing)
        show_pc: Flag to enable PC tracking display
        quiet: Suppress output during parsing (for execution mode)
    """
    
    def __init__(self):
        """
        Initialize the parser with empty instruction list and components.
        
        Creates a fresh parser state with:
        - Empty instruction list
        - Register bank for PC tracking
        - Memory for future execution support
        """
        self.instructions = []           # Parsed instruction objects
        self.line_number = 0             # Current line in source file
        self.registers = ARM64Registers()  # Register bank for PC tracking
        self.memory = ARM64Memory(size=256, base_address=0x7FFFFF00)  # Stack memory
        self.show_pc = False             # Display PC tracking (Task 4)
        self.quiet = False               # Suppress output for execution mode

    def parse_file(self, filename, show_pc=False, quiet=False):
        """
        Parse an ARM64 assembly file line by line.
        
        Main entry point for parsing. Reads the entire file, processes each
        line to extract instructions, and builds the instruction list while
        tracking the Program Counter progression.
        
        Args:
            filename (str): Path to the assembly file to parse
            show_pc (bool): Whether to show PC updates during parsing (Task 4)
                          Enables display of how PC advances through code
            quiet (bool): Suppress parsing output (used during execution)
                         Allows parsing without console output
        
        Process:
        1. Reset parser state
        2. Initialize PC to 0x0 (start of code)
        3. Initialize SP to high memory (stack grows down)
        4. Read file line by line
        5. Parse each instruction and update PC by 4
        
        The PC tracking (Task 4) helps understand how branch targets work
        and how the processor steps through instructions sequentially.
        """
        self.show_pc = show_pc
        self.quiet = quiet

        # Clear any previous parsing state
        self.instructions = []
        self.registers.reset()
        self.memory.clear()

        # Reset PC to 0x0 at start of parsing (Task 4)
        # This simulates how code is loaded at address 0 in our emulator
        self.registers.set_pc(0x0)

        # Initialize SP to point near end of stack
        # Stack grows downward from high addresses in ARM64
        # We leave 16 bytes at the very top as a buffer
        initial_sp = self.memory.base_address + self.memory.size - 16
        self.registers.set_sp(initial_sp)

        # Display initial state if PC tracking is enabled
        if self.show_pc and not self.quiet:
            print(f"\n=== Task 4: PC Tracking During Parsing ===")
            print(f"Initial PC: 0x{self.registers.get_pc():08x}")
            print(f"Initial SP: 0x{self.registers.get_sp():016x}")
            print("-" * 60)
        
        # Read the assembly file
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        # Process each line of the assembly file
        for line_num, line in enumerate(lines, 1):
            # Skip empty lines (just whitespace)
            line = line.strip()
            if not line:
                continue
            
            # Parse the instruction line
            self.line_number = line_num
            self.parse_line(line, line_num)
    
    def parse_line(self, line, line_num):
        """
        Parse a single line of ARM64 assembly.
        
        Extracts instruction components from a line and creates an Instruction
        object. Updates PC after parsing each instruction (Task 4).
        
        Expected format:
            address: machine_code    instruction operands    ; comment
            Example: 0: d10043ff    sub sp, sp, #0x10    ; allocate stack
        
        The format comes from disassembler output where:
        - address: Memory location of instruction (hex)
        - machine_code: 32-bit instruction encoding (hex)
        - instruction: Mnemonic like 'add', 'sub', 'mov'
        - operands: Registers, immediates, or memory references
        - comment: Optional explanation after semicolon
        
        Args:
            line (str): The assembly line to parse
            line_num (int): Line number for display and error messages
        """
        # Split by tabs to separate the three main components
        # Tab-delimited format is standard for disassembler output
        parts = line.split('\t')
        
        if len(parts) < 3:
            # Line doesn't have expected format, skip it
            # Could be a comment or malformed line
            return
        
        # Extract address (before the colon)
        # Format: "0:" or "4:" or "8:" etc.
        address_part = parts[0].strip()
        if ':' in address_part:
            address = address_part.split(':')[0].strip()
        else:
            # No colon means invalid format
            return
        
        # Machine code is in second tab-delimited field
        # This is the 32-bit encoded instruction (8 hex digits)
        machine_code = parts[1].strip()
        
        # The rest contains instruction mnemonic and operands
        # May have comments after semicolon or //
        instruction_part = ' '.join(parts[2:]).strip()
        
        # Remove comments (anything after // or descriptive text)
        # Comments provide human-readable explanations but aren't executed
        if '//' in instruction_part:
            instruction_part = instruction_part.split('//')[0].strip()
        
        # Sometimes there's additional text after tabs, remove it
        if '\t' in instruction_part:
            instruction_part = instruction_part.split('\t')[0].strip()
        
        # Create instruction object and parse it
        try:
            # Get current PC value before incrementing (Task 4)
            current_pc = self.registers.get_pc()
            
            # Create instruction object with extracted components
            instruction = Instruction(address, machine_code, instruction_part)
            
            # Parse the instruction to extract mnemonic and operands
            instruction.parse()
            
            # Store the PC value with the instruction (Task 4)
            instruction.pc_value = current_pc
            
            # Display the parsed instruction (with PC info if requested)
            if not self.quiet:
                if self.show_pc:
                    # Show detailed PC tracking information
                    self.display_instruction_with_pc(instruction, line_num, current_pc)
                else:
                    # Standard instruction display
                    self.display_instruction(instruction, line_num)
            
            # Add to our instruction list
            self.instructions.append(instruction)
            
            # Increment PC by 4 bytes for next instruction (Task 4)
            self.registers.increment_pc(4)
            
        except Exception as e:
            print(f"Error parsing line {line_num}: {e}")
    
    def display_instruction(self, instruction, line_num):
        """
        Display a parsed instruction.
        
        Shows the instruction breakdown with mnemonic and operands
        in a structured format.
        
        Args:
            instruction (Instruction): The parsed instruction object
            line_num (int): Line number for display header
        
        Output format:
            -------------------------Instruction #1:
            -------------------------
            Instruction: SUB
            Operand #1: sp
            Operand #2: sp
            Operand #3: #0x10
        """
        # Print section header with instruction number
        print("-" * 125 + f"Instruction #{line_num}:")
        print("-" * 125)
        
        # Print instruction mnemonic in uppercase
        print(f"Instruction: {instruction.mnemonic.upper()}")
        
        # Print each operand
        operand_num = 1
        for i, operand in enumerate(instruction.operands):
            # Special handling for branch targets with labels
            if '<' in operand and '>' in operand:
                # This is a label like <main+0x40>
                # Extract the content and format with arrow
                label_content = operand[1:-1]  # Remove < and >
                formatted = label_content.replace('+', ' + ')
                print(f"Operand #{operand_num}: {operand} --> {formatted}")
            elif '[' in operand and ']' in operand and '-->' in operand:
                # Memory operand already formatted by instruction parser
                print(f"Operand #{operand_num}: {operand}")
            else:
                # Regular operand (register or immediate)
                print(f"Operand #{operand_num}: {operand}")
            operand_num += 1
        
        print()  # Empty line after each instruction
    
    def display_instruction_with_pc(self, instruction, line_num, pc_value):
        """
        Display a parsed instruction with PC tracking information (Task 4).
        
        Enhanced display showing how the Program Counter advances through
        the code, correlating PC values with instruction addresses.
        
        Args:
            instruction (Instruction): The parsed instruction object
            line_num (int): Line number for display
            pc_value (int): Current PC value for this instruction
        """
        # Print header with PC tracking info
        print("-" * 125 + f"Instruction #{line_num}:")
        print("-" * 125)
        
        # Show PC and address correlation (Task 4)
        print(f"PC: 0x{pc_value:08x} | Address: 0x{instruction.address:>2s} | Machine Code: {instruction.machine_code}")
        
        # Print instruction mnemonic
        print(f"Instruction: {instruction.mnemonic.upper()}")
        
        # Print operands with special formatting for complex types
        operand_num = 1
        for i, operand in enumerate(instruction.operands):
            # Check if operand is a branch target with label
            if '<' in operand and '>' in operand:
                # Label format: <main+0x40> means main function + offset
                label_content = operand[1:-1]  # Remove angle brackets
                formatted = label_content.replace('+', ' + ')
                print(f"Operand #{operand_num}: {operand} --> {formatted}")
            elif '[' in operand and ']' in operand and '-->' in operand:
                # Memory operand with computed address
                print(f"Operand #{operand_num}: {operand}")
            else:
                # Simple operand (register or immediate)
                print(f"Operand #{operand_num}: {operand}")
            operand_num += 1
        
        # Show next PC value (Task 4)
        next_pc = pc_value + 4
        print(f"Next PC will be: 0x{next_pc:08x} (current + 4)")
        
        print()  # Empty line after each instruction
    
    def display_pc_summary(self):
        """
        Display a summary of PC values for all parsed instructions (Task 4).
        
        Shows how the Program Counter progressed through the entire program,
        providing a map of PC values to instructions. 
        """
        print("\n" + "="*125)
        print("Program Counter Summary")
        print("="*125)
        print(f"Total instructions parsed: {len(self.instructions)}")
        print(f"Final PC value: 0x{self.registers.get_pc():08x}")
        print("\nPC values for each instruction:")
        print("-"*60)
        
        # Show PC mapping for each instruction
        for i, instr in enumerate(self.instructions, 1):
            if hasattr(instr, 'pc_value'):
                # Display concise summary line
                # Truncate operands for readability
                operand_str = ' '.join(instr.operands[:2])[:30]
                print(f"  {i:2}. PC: 0x{instr.pc_value:08x} | "
                      f"Address: 0x{instr.address:>2s} | "
                      f"{instr.mnemonic.upper():6} {operand_str}")
        
        # Summary statistics
        print("-"*60)
        print(f"PC started at: 0x00000000")
        print(f"PC ended at:   0x{self.registers.get_pc():08x}")
        print(f"Total bytes:   {self.registers.get_pc()} (decimal)")
        print(f"Instructions:  {len(self.instructions)} x 4 bytes = {len(self.instructions) * 4} bytes")