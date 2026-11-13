================================================================================
                            ARM64 EMULATOR README
================================================================================
By Ryan Godburn and Arjun Aravind

OVERVIEW
--------
This is an educational ARM64 assembly emulator that simulates a subset of ARM64
instructions. It parses and executes ARM64 assembly code, maintaining registers
and stack memory to demonstrate how ARM processors work at the instruction level.

REQUIREMENTS
------------
- Python 3.6 or higher
- No external dependencies required

QUICK START
-----------
1. Parse an assembly file:
   python main.py -p test1.txt

2. Execute an assembly file:
   python main.py -x test1.txt

3. Execute with trace (see each instruction as it runs):
   python main.py -x test1.txt --trace

COMMAND LINE OPTIONS
--------------------
Basic Operations:
  -p, --parse <file>      Parse assembly file and display instruction breakdown
  -x, --execute <file>    Execute assembly file (runs the program)
  -r, --registers         Display register state
  -m, --memory           Display stack memory hexdump

Advanced Options:
  --pc                   Track Program Counter during parsing
  --trace                Show step-by-step execution (only with -x)

USAGE EXAMPLES
--------------
1. Parse only (analyze without executing):
   python main.py -p test1.txt
   
   This shows how each instruction is broken down into its components.

2. Execute program:
   python main.py -x test1.txt
   
   Runs the program and shows final execution summary.

3. Execute with full trace:
   python main.py -x test1.txt --trace
   
   Shows each instruction as it executes with register/memory changes.

4. Parse with PC tracking:
   python main.py -p test1.txt --pc
   
   Shows how the Program Counter advances through the code.

5. Execute and show final state:
   python main.py -x test1.txt -r -m
   
   Executes and displays final register and memory state.

6. Show initial state only:
   python main.py -r
   python main.py -m
   
   Displays initial (empty) register or memory state.

INPUT FILE FORMAT
-----------------
The emulator expects ARM64 assembly in the following format:
   address: machine_code    instruction operands

Example:
   0: d10043ff    sub sp, sp, #0x10
   4: d2800f60    mov x0, #0x7b
   8: f90007e0    str x0, [sp, #8]

This format is typical of disassembler output.

SUPPORTED INSTRUCTIONS
----------------------
Arithmetic:
  ADD  - Addition (Rd = Rn + Rm/immediate)
  SUB  - Subtraction (Rd = Rn - Rm/immediate)
  MUL  - Multiplication (Rd = Rn * Rm)

Logical:
  AND  - Bitwise AND
  EOR  - Bitwise XOR (exclusive OR)

Data Movement:
  MOV  - Move/copy value

Memory Operations:
  STR  - Store register (64/32-bit)
  STRB - Store byte
  LDR  - Load register (64/32-bit)
  LDRB - Load byte

Control Flow:
  B    - Unconditional branch
  B.GT - Branch if greater than
  B.LE - Branch if less than or equal
  CMP  - Compare (sets flags)
  RET  - Return (ends execution)

Miscellaneous:
  NOP  - No operation

REGISTER SUPPORT
----------------
64-bit registers: X0-X30, XZR (zero register), SP (stack pointer), PC
32-bit registers: W0-W30, WZR (lower 32 bits of X registers)

Writing to a W register zeros the upper 32 bits of the corresponding X register.

MEMORY MODEL
------------
- 256 bytes of stack memory
- Default base address: 0x7FFFFF00
- Stack grows downward (SP decreases when allocating)
- Little-endian byte ordering

TRACE OUTPUT FORMAT
-------------------
When using --trace, each instruction shows:
  PC: 0x00000000 | Executing: SUB sp, sp, #0x10
    SP = 0x7fffffef

This shows the PC value, the instruction executed, and any state changes.

EXECUTION FLOW
--------------
1. All registers start at 0
2. PC starts at 0x0
3. SP is initialized to near the top of stack (0x7FFFFFEF)
4. Instructions execute sequentially (PC += 4) unless a branch occurs
5. Execution stops when RET is encountered

================================================================================