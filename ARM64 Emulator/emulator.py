"""
ARM64 Emulator Module
Written by: Ryan Godburn and Arjun Aravind

Implements the instruction execution engine for the ARM64 emulator. This module
takes parsed instructions and actually executes them, modifying registers and
memory.

Key Parts:
- Execute parsed ARM64 instructions in sequence
- Modify register and memory state based on instruction semantics
- Handle control flow (branches, returns)
- Track comparison results for conditional branches
- Support both 64-bit and 32-bit operations

Task 5: Execute parsed ARM64 instructions
Task 6: Handle 32-bit register execution semantics

Execution Model:
1. Fetch instruction at current PC
2. Decode and execute the instruction
3. Update registers/memory as needed
4. Advance PC to next instruction (or branch)
5. Continue until RET instruction or max steps
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from instruction import Instruction
from memory import ARM64Memory
from registers import ARM64Registers
from utils import (
    get_register_size,
    is_immediate,
    is_register,
    parse_immediate_value,
)


class ARM64Emulator:
    """
    Execute ARM64 instructions previously parsed by ARM64Parser.
    
    This class simulates the execution pipeline of an ARM64 processor,
    fetching instructions based on the Program Counter, decoding them,
    and performing the requested operations on registers and memory.
    
    The emulator maintains:
    - Instruction list from parser
    - Register state (31 general + special registers)
    - Memory state (256-byte stack)
    - Execution state (running, comparison results)
    - PC-to-instruction mapping for branches
    
    Execution continues until:
    - A RET instruction is encountered
    - Maximum step count is reached (safety)
    - An error occurs
    """

    def __init__(
        self,
        instructions: Optional[List[Instruction]] = None,
        registers: Optional[ARM64Registers] = None,
        memory: Optional[ARM64Memory] = None,
    ) -> None:
        """
        Initialize the emulator with instructions and hardware components.
        Written by: Ryan Godbunrn and Arjun Aravind
        
        Args:
            instructions: List of parsed Instruction objects to execute
            registers: Register bank (created if not provided)
            memory: Stack memory (created if not provided)
        """
        # Core components
        self.instructions: List[Instruction] = instructions or []
        self.registers = registers or ARM64Registers()
        self.memory = memory or ARM64Memory(size=256, base_address=0x7FFFFF00)

        # Execution state
        self.trace: bool = False           # Enable instruction tracing
        self.running: bool = False         # Execution active flag
        self.last_cmp_result: Optional[int] = None  # Result of last CMP (signed)
        self.last_cmp_bits: int = 64       # Bit width of last comparison

        # PC to instruction mapping for efficient branch target lookup
        self.pc_index_map: Dict[int, int] = {}
        
        # Stack configuration
        self.stack_start = self.memory.base_address + self.memory.size - 16

        # Instruction dispatch table for O(1) handler lookup
        # Maps mnemonics to their execution methods
        self.dispatch_table: Dict[str, Callable[[Instruction], None]] = {
            # Arithmetic operations
            'add': self.exec_add,      # Addition
            'sub': self.exec_sub,      # Subtraction
            'mul': self.exec_mul,      # Multiplication

            # Logical operations
            'and': self.exec_and,      # Bitwise AND
            'eor': self.exec_eor,      # Bitwise XOR (exclusive OR)

            # Data movement
            'mov': self.exec_mov,      # Move/copy value

            # Memory operations
            'str': self.exec_str,      # Store register (word/doubleword)
            'strb': self.exec_strb,    # Store register byte
            'ldr': self.exec_ldr,      # Load register (word/doubleword)
            'ldrb': self.exec_ldrb,    # Load register byte

            # Control flow
            'b': self.exec_b,          # Unconditional branch
            'b.gt': self.exec_b_gt,    # Branch if greater than
            'b.le': self.exec_b_le,    # Branch if less than or equal
            'cmp': self.exec_cmp,      # Compare (sets flags)
            'ret': self.exec_ret,      # Return from function

            # Miscellaneous
            'nop': self.exec_nop,      # No operation
        }

        # Temporary storage for memory updates during instruction execution
        self._current_memory_updates: List[Tuple[int, int, int]] = []

    def execute(
        self,
        trace: bool = False,
        reset_state: bool = True,
        max_steps: Optional[int] = None,
        state_callback: Optional[Callable[["ARM64Emulator"], None]] = None,
    ) -> int:
        """
        Execute instructions until a RET is encountered.
        Written by: Ryan Godburn

        Main execution loop that simulates the fetch-decode-execute cycle
        of a real processor. Starts at PC=0 and continues until a return
        instruction or maximum step count.

        Args:
            trace: Print each instruction before executing it
                  Shows instruction text and state changes
            reset_state: Reset registers and memory to clean state before execution
                        Ensures consistent starting conditions
            max_steps: Optional safety guard to stop after N instructions
                      Prevents infinite loops during debugging
            state_callback: Optional callable invoked after initialization
                          but before first instruction (for displaying initial state)

        Returns:
            int: Number of instructions executed

        Process:
        1. Build PC-to-instruction mapping
        2. Initialize state (reset if requested)
        3. Main execution loop:
           a. Fetch instruction at current PC
           b. Execute instruction (may modify PC)
           c. Update PC if not modified by instruction
           d. Display trace if enabled
           e. Check termination conditions
        """
        if not self.instructions:
            return 0

        # Configure execution parameters
        self.trace = trace
        self.running = True
        self.last_cmp_result = None
        self.last_cmp_bits = 64
        
        # Build mapping from PC values to instruction indices
        # This allows O(1) branch target resolution
        self.build_pc_index_map()

        # Initialize hardware state
        if reset_state:
            self.registers.reset()
            self.memory.clear()

        # Start execution at address 0
        self.registers.set_pc(0)
        
        # Initialize stack pointer if needed
        if reset_state or self.registers.get_sp() == 0:
            self.registers.set_sp(self.stack_start)

        # Clear any previous update logs
        self.registers.clear_update_log()

        # Call state callback if provided (for showing initial state)
        if state_callback is not None:
            state_callback(self)

        steps = 0  # Instruction counter

        # Main execution loop - continues until RET or error
        while self.running:
            # Fetch: Get current PC and find corresponding instruction
            pc = self.registers.get_pc()
            instr_index = self.pc_index_map.get(pc)
            if instr_index is None:
                raise RuntimeError(f"No instruction mapped at PC 0x{pc:08x}")

            instruction = self.instructions[instr_index]

            # Prepare for tracking state changes
            self.registers.clear_update_log()
            self._current_memory_updates = []

            # Calculate default next PC (current + 4)
            # Branch instructions will override this
            next_pc = (pc + 4) & 0xFFFFFFFFFFFFFFFF
            
            # Decode and Execute: Call appropriate handler
            handler = self.get_handler(instruction.mnemonic)
            handler(instruction)
            
            # Capture state changes for tracing
            post_pc = self.registers.get_pc()
            reg_updates = self.registers.consume_update_log()
            mem_updates = list(self._current_memory_updates)

            # Display execution trace if enabled
            if self.trace:
                self.print_trace(pc, instruction, reg_updates, mem_updates, post_pc)

            steps += 1

            # Check termination conditions
            if not self.running:  # RET instruction was executed
                break

            # Update PC if not modified by instruction (normal sequential flow)
            if self.registers.get_pc() == pc:
                self.registers.set_pc(next_pc)

            # Safety check: prevent infinite loops
            if max_steps is not None and steps >= max_steps:
                break

        return steps

    def build_pc_index_map(self) -> None:
        """
        Build a mapping from PC values to instruction list indices.
        Written by: Arjun Aravind
        
        This allows O(1) lookup of instructions by their PC value,
        which is essential for efficient branch target resolution.
        
        Each instruction has a pc_value field set during parsing that
        indicates what PC value corresponds to that instruction.
        """
        self.pc_index_map = {
            instr.pc_value: index for index, instr in enumerate(self.instructions)
        }

    def print_trace(
        self,
        pc: int,
        instruction: Instruction,
        reg_updates: List[Tuple[str, int, int]],
        mem_updates: List[Tuple[int, int, int]],
        post_pc: int,
    ) -> None:
        """
        Print execution trace for debugging.
        Written by: Arjun Aravind
        
        Shows what instruction was executed and how it changed state.
        Format matches common debugger output for easy reading.
        
        Args:
            pc: PC value before executing instruction
            instruction: The instruction that was executed
            reg_updates: List of (register, value, bits) tuples
            mem_updates: List of (address, value, bits) tuples
            post_pc: PC value after executing instruction
        
        Output format:
            PC: 0x00000000 | Executing: SUB sp, sp, #0x10
              SP = 0x7fffffef
        """
        # Format instruction text for display
        inst_text = instruction.instruction_text.strip()
        if inst_text:
            # Uppercase the mnemonic but preserve operand case
            parts = inst_text.split(None, 1)
            inst_text = parts[0].upper()
            if len(parts) > 1:
                inst_text += f" {parts[1]}"
        else:
            inst_text = instruction.mnemonic.upper()

        print(f"PC: 0x{pc:08x} | Executing: {inst_text}")

        # Check if PC was modified (branch occurred)
        pc_changed = post_pc != pc

        # Display state changes
        if not reg_updates and not mem_updates and not pc_changed:
            print("  (no state change)")  # NOP or similar
        else:
            # Show register updates
            for name, value, bits in reg_updates:
                width = self.hex_width(bits)
                print(f"  {name} = 0x{value:0{width}x}")

            # Show memory updates
            for address, value, bits in mem_updates:
                width = self.hex_width(bits)
                print(f"  MEM[0x{address:016x}] = 0x{value:0{width}x}")

            # Show PC change if branch occurred
            if pc_changed:
                print(f"  PC = 0x{post_pc:016x}")
        print()

    def hex_width(self, bits: int) -> int:
        """
        Calculate hex digit width for a given bit count.
        Written by: Arjun Aravind
        
        Determines how many hex digits are needed to represent
        a value of the given bit width.
        """
        if bits >= 64:
            return 16  # 64 bits = 16 hex digits
        if bits == 32:
            return 8   # 32 bits = 8 hex digits
        if bits == 16:
            return 4   # 16 bits = 4 hex digits
        if bits == 8:
            return 2   # 8 bits = 2 hex digits
        return max(2, bits // 4)  # General case

    def get_handler(self, mnemonic: str) -> Callable[[Instruction], None]:
        """
        Get the execution handler for an instruction mnemonic.
        Written by: Ryan Godburn
        
        Uses dispatch table for O(1) lookup of instruction handlers.
        """
        handler = self.dispatch_table.get(mnemonic)
        if handler is None:
            raise NotImplementedError(f"Instruction '{mnemonic}' not implemented")
        return handler

    def record_memory_write(self, address: int, value: int, bits: int) -> None:
        """
        Record a memory write for trace output.
        Written by: Ryan Godburn
        """
        if bits >= 64:
            masked = value & 0xFFFFFFFFFFFFFFFF
        else:
            masked = value & ((1 << bits) - 1)
        self._current_memory_updates.append((address, masked, bits))

    def mask_to_bits(self, value: int, bits: int) -> int:
        """
        Mask a value to fit in the specified number of bits.
        Written by: Arjun Aravind
        
        Simulates hardware register/memory width constraints.
        """
        if bits >= 64:
            return value & 0xFFFFFFFFFFFFFFFF
        return value & ((1 << bits) - 1)

    def to_signed(self, value: int, bits: int) -> int:
        """
        Convert unsigned value to signed using two's complement.
        Written by: Arjun Aravind
        
        ARM64 uses two's complement for signed integers. This converts
        an unsigned value to its signed interpretation.
        
        Example:
            0xFF (8-bit) = 255 unsigned = -1 signed
            0x80 (8-bit) = 128 unsigned = -128 signed
        """
        mask = (1 << bits) - 1
        value &= mask
        sign_bit = 1 << (bits - 1)
        # If sign bit is set, extend with 1s (negative)
        return value - (1 << bits) if value & sign_bit else value

    def read_operand(self, operand: str, bits: Optional[int] = None) -> int:
        """
        Read value from an operand (register or immediate).
        Written by: Arjun Aravind
        
        Handles different operand types:
        - Immediate values (#123, #0xFF)
        - Register values (X0, W0, SP)
        
        Args:
            operand: Operand string from instruction
            bits: Optional bit width for masking
        
        Returns:
            Integer value of the operand
        """
        if is_immediate(operand):
            value = parse_immediate_value(operand)
            if value is None:
                raise ValueError(f"Invalid immediate value: {operand}")
        elif is_register(operand):
            value = self.registers.read(operand)
        else:
            raise ValueError(f"Unsupported operand: {operand}")

        # Mask to requested bit width if specified
        if bits is not None:
            value = self.mask_to_bits(value, bits)
        return value

    def resolve_memory_address(self, instruction: Instruction) -> int:
        """
        Calculate effective address for memory operations.
        Written by: Ryan Godburn
        
        Handles address modes like:
        - [SP]: Direct register addressing
        - [SP, #16]: Register + immediate offset
        - [X0, X1]: Register + register offset
        
        Returns:
            Calculated memory address
        """
        # Get memory metadata from instruction
        mem_info = instruction.metadata.get('memory') if hasattr(instruction, 'metadata') else None
        if not mem_info:
            raise ValueError(
                f"Instruction '{instruction.instruction_text}' lacks memory metadata"
            )

        # Get base register value
        base = mem_info.get('base')
        if base is None:
            raise ValueError(
                f"Invalid memory operand for '{instruction.instruction_text}'"
            )

        address = self.registers.read(base)
        
        # Add offset if present
        offset = mem_info.get('offset')
        if offset:
            if is_immediate(offset):
                immediate = parse_immediate_value(offset)
                if immediate is None:
                    raise ValueError(f"Invalid immediate offset: {offset}")
                address += immediate
            elif is_register(offset):
                address += self.registers.read(offset)
            else:
                raise ValueError(f"Unsupported memory offset: {offset}")

        return address

    def get_branch_target(self, instruction: Instruction) -> int:
        """
        Extract branch target address from instruction.
        Written by: Arjun Aravind
        
        Branch targets can be:
        - Absolute addresses (0x2c)
        - Labels (<main+0x2c>)
        
        Returns PC value to branch to.
        """
        branch_info = instruction.metadata.get('branch') if hasattr(instruction, 'metadata') else None

        if branch_info and branch_info.get('target') is not None:
            return branch_info['target']

        # Fallback: try to parse first operand as hex address
        if instruction.operands:
            target_str = instruction.operands[0]
            try:
                return int(target_str, 16)
            except ValueError as exc:
                raise ValueError(f"Unable to parse branch target '{target_str}'") from exc

        raise ValueError(f"Instruction '{instruction.instruction_text}' lacks branch target")

    def branch(self, instruction: Instruction, condition: bool) -> None:
        """
        Execute a conditional or unconditional branch.
        Written by: Arjun Aravind
        
        Updates PC to branch target if condition is true.
        For unconditional branches, condition is always True.
        """
        if not condition:
            return  # Condition not met, continue sequentially

        # Get target PC and validate it exists
        target = self.get_branch_target(instruction)
        if target not in self.pc_index_map:
            raise RuntimeError(f"Branch target 0x{target:08x} not found")

        # Update PC to branch target
        self.registers.set_pc(target)

    # ==================== Instruction Handlers ====================
    # Each handler implements the semantics of one instruction type

    def exec_add(self, instruction: Instruction) -> None:
        """
        Execute ADD instruction: Rd = Rn + Rm/immediate
        Written by: Arjun Aravind
        
        Performs addition and stores result in destination register.
        Bit width determined by destination register (X=64, W=32).
        """
        dest, op1, op2 = instruction.operands
        bits = get_register_size(dest)
        result = (
            self.read_operand(op1, bits)
            + self.read_operand(op2, bits)
        )
        result = self.mask_to_bits(result, bits)
        self.registers.write(dest, result)

    def exec_sub(self, instruction: Instruction) -> None:
        """
        Execute SUB instruction: Rd = Rn - Rm/immediate
        Written by: Arjun Aravind
        
        Performs subtraction and stores result in destination.
        Commonly used for stack frame allocation (sub sp, sp, #16).
        """
        dest, op1, op2 = instruction.operands
        bits = get_register_size(dest)
        result = (
            self.read_operand(op1, bits)
            - self.read_operand(op2, bits)
        )
        result = self.mask_to_bits(result, bits)
        self.registers.write(dest, result)

    def exec_and(self, instruction: Instruction) -> None:
        """
        Execute AND instruction: Rd = Rn & Rm/immediate
        Written by: Ryan Godburn
        
        Performs bitwise AND for masking operations.
        """
        dest, op1, op2 = instruction.operands
        bits = get_register_size(dest)
        result = self.read_operand(op1, bits) & self.read_operand(op2, bits)
        self.registers.write(dest, self.mask_to_bits(result, bits))

    def exec_eor(self, instruction: Instruction) -> None:
        """
        Execute EOR instruction: Rd = Rn ^ Rm/immediate
        Written by: Ryan Godburn
        
        Performs bitwise XOR (exclusive OR).
        Can be used to toggle bits or clear register (eor x0, x0, x0).
        """
        dest, op1, op2 = instruction.operands
        bits = get_register_size(dest)
        result = self.read_operand(op1, bits) ^ self.read_operand(op2, bits)
        self.registers.write(dest, self.mask_to_bits(result, bits))

    def exec_mul(self, instruction: Instruction) -> None:
        """
        Execute MUL instruction: Rd = Rn * Rm
        Written by: Arjun Aravind
        
        Performs multiplication. Result is truncated to register width.
        """
        dest, op1, op2 = instruction.operands
        bits = get_register_size(dest)
        result = self.read_operand(op1, bits) * self.read_operand(op2, bits)
        self.registers.write(dest, self.mask_to_bits(result, bits))

    def exec_mov(self, instruction: Instruction) -> None:
        """
        Execute MOV instruction: Rd = Rm/immediate
        Written by: Ryan Godburn
        
        Copies value to destination register. Common for initialization
        and register-to-register transfers.
        """
        dest, src = instruction.operands
        bits = get_register_size(dest)
        value = self.read_operand(src, bits)
        self.registers.write(dest, self.mask_to_bits(value, bits))

    def exec_str(self, instruction: Instruction) -> None:
        """
        Execute STR instruction: Store register to memory
        Written by: Ryan Godburn
        
        Stores 32-bit (W register) or 64-bit (X register) value.
        Memory address calculated from base + offset.
        """
        dest_reg = instruction.operands[0]
        bits = get_register_size(dest_reg)
        address = self.resolve_memory_address(instruction)
        value = self.mask_to_bits(self.registers.read(dest_reg), bits)

        # Store appropriate size
        if bits == 64:
            self.memory.write_64(address, value)
        elif bits == 32:
            self.memory.write_32(address, value)
        else:
            self.memory.write(address, value, bits // 8)
        
        self.record_memory_write(address, value, bits)

    def exec_strb(self, instruction: Instruction) -> None:
        """
        Execute STRB instruction: Store register byte to memory
        Written by: Ryan Godburn
        
        Stores only the lowest 8 bits of register to memory.
        """
        dest_reg = instruction.operands[0]
        address = self.resolve_memory_address(instruction)
        value = self.registers.read(dest_reg) & 0xFF  # Get lowest byte
        self.memory.write_byte(address, value)
        self.record_memory_write(address, value, 8)

    def exec_ldr(self, instruction: Instruction) -> None:
        """
        Execute LDR instruction: Load register from memory
        Written by: Ryan Godburn
        
        Loads 32-bit or 64-bit value from memory into register.
        """
        dest_reg = instruction.operands[0]
        bits = get_register_size(dest_reg)
        address = self.resolve_memory_address(instruction)

        # Load appropriate size
        if bits == 64:
            value = self.memory.read_64(address)
        elif bits == 32:
            value = self.memory.read_32(address)
        else:
            value = self.memory.read(address, bits // 8)

        self.registers.write(dest_reg, value)

    def exec_ldrb(self, instruction: Instruction) -> None:
        """
        Execute LDRB instruction: Load register byte from memory
        Written by: Ryan Godburn
        
        Loads single byte from memory, zero-extends to register width.
        """
        dest_reg = instruction.operands[0]
        address = self.resolve_memory_address(instruction)
        value = self.memory.read_byte(address)
        self.registers.write(dest_reg, value)  # Automatic zero-extension

    def exec_nop(self, instruction: Instruction) -> None:
        """
        Execute NOP instruction: No operation
        Written by: Arjun Aravind
        
        Does nothing. Used for timing, alignment, or placeholders.
        """
        return

    def exec_b(self, instruction: Instruction) -> None:
        """
        Execute B instruction: Unconditional branch
        Written by: Arjun Aravind
        
        Jumps to specified address/label.
        """
        self.branch(instruction, True)

    def exec_b_gt(self, instruction: Instruction) -> None:
        """
        Execute B.GT instruction: Branch if greater than
        Written by: Arjun Aravind
        
        Branches if last comparison showed first > second (signed).
        """
        if self.last_cmp_result is None:
            raise RuntimeError("B.GT encountered before CMP")
        self.branch(instruction, self.last_cmp_result > 0)

    def exec_b_le(self, instruction: Instruction) -> None:
        """
        Execute B.LE instruction: Branch if less than or equal
        Written by: Arjun Aravind
        
        Branches if last comparison showed first <= second (signed).
        """
        if self.last_cmp_result is None:
            raise RuntimeError("B.LE encountered before CMP")
        self.branch(instruction, self.last_cmp_result <= 0)

    def exec_cmp(self, instruction: Instruction) -> None:
        """
        Execute CMP instruction: Compare two values
        Written by: Arjun Aravind
        
        Performs subtraction without storing result, only sets flags.
        Result saved for conditional branches (b.gt, b.le, etc.).
        """
        op1, op2 = instruction.operands
        bits = get_register_size(op1)

        # Read operand values
        value1 = self.read_operand(op1, bits)
        value2 = self.read_operand(op2, bits)

        # Perform subtraction and update flags
        diff = self.mask_to_bits(value1 - value2, bits)
        self.registers.update_flags(diff, is_64bit=(bits == 64))

        # Store signed comparison result for conditional branches
        signed1 = self.to_signed(value1, bits)
        signed2 = self.to_signed(value2, bits)
        self.last_cmp_result = signed1 - signed2
        self.last_cmp_bits = bits

    def exec_ret(self, instruction: Instruction) -> None:
        """
        Execute RET instruction: Return from function
        Written by: Arjun Aravind
        
        Sets PC to value in X30 (link register) and stops execution.
        This is how functions return to their caller.
        """
        self.registers.set_pc(self.registers.read('X30'))
        self.running = False  # Stop execution