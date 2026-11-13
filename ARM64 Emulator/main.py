#!/usr/bin/env python3
"""
ARM64 Emulator - Main Entry Point
Written by: Ryan Godburn

This is the primary entry point for the ARM64 assembly emulator. 

Architecture Notes:
- ARM64 uses 64-bit registers (X0-X30) with 32-bit views (W0-W30)
- Instructions are always 32 bits (4 bytes) in length
- Stack grows downward from high memory addresses
- PC increments by 4 after each instruction (except branches)
"""

import argparse
import sys
from emulator import ARM64Emulator
from parser import ARM64Parser
from registers import ARM64Registers
from memory import ARM64Memory


def main():
    """
    Main entry point for the ARM64 emulator.
    
    This function:
    1. Parses command-line arguments to determine operation mode
    2. Initializes the core emulator components (registers, memory)
    3. Routes execution to appropriate functionality (parse, execute, display)
    4. Handles error conditions and provides user feedback
    
    The emulator can operate in several modes:
    - Parse mode: Analyzes assembly files without execution
    - Execute mode: Runs the instructions and modifies state
    - Display mode: Shows register/memory state
    - Trace mode: Step-by-step execution debugging
    """
    # Set up command line argument parser with detailed help messages
    arg_parser = argparse.ArgumentParser(
        description='ARM64 Assembly Emulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s -p program.s          # Parse assembly file
  %(prog)s -x program.s          # Execute assembly file
  %(prog)s -x program.s --trace  # Execute with instruction tracing
  %(prog)s -p program.s --pc     # Parse with PC tracking
  %(prog)s -r                    # Display initial register state
  %(prog)s -m                    # Display initial memory state
        '''
    )
    
    # File operation arguments
    arg_parser.add_argument('-p', '--parse',
                           type=str,
                           metavar='filename',
                           help='Parse ARM64 assembly file and display instruction breakdown')
    arg_parser.add_argument('-x', '--execute',
                           type=str,
                           metavar='filename',
                           help='Execute ARM64 assembly file (runs instructions)')
    
    # State display arguments
    arg_parser.add_argument('-r', '--registers',
                           action='store_true',
                           help='Display register state (all 31 general purpose + special)')
    arg_parser.add_argument('-m', '--memory',
                           action='store_true',
                           help='Display stack memory hexdump (256 bytes)')
    
    # Debugging and tracing arguments
    arg_parser.add_argument('--pc', '--program-counter',
                           action='store_true',
                           help='Track PC during parsing to see instruction addresses')
    arg_parser.add_argument('--trace',
                           action='store_true',
                           help='Trace instruction execution (shows each step)')
    
    args = arg_parser.parse_args()
    
    # Validate that at least one argument was provided
    if not any(vars(args).values()):
        arg_parser.print_help()
        sys.exit(1)

    # Validate that trace is only used with execute
    if args.trace and not args.execute:
        print("Error: --trace can only be used together with --execute.")
        sys.exit(1)
    
    # Initialize core emulator components
    # Registers: 31 general purpose (X0-X30) + SP, PC, XZR
    registers = ARM64Registers()
    
    # Memory: 256 bytes of stack space at high memory address
    memory = ARM64Memory(size=256, base_address=0x7FFFFF00)
    
    # Handle standalone memory display (no file operations)
    if args.memory and not args.parse and not args.execute:
        print("Initial Stack Memory State:")
        memory.display()

    # Handle standalone register display (no file operations)
    if args.registers and not args.parse and not args.execute:
        print("Initial Register State:")
        registers.display()
    
    # ==================== EXECUTION MODE ====================
    # Task 5: Execute parsed instructions and modify emulator state
    if args.execute:
        parser = ARM64Parser()

        try:
            # Parse file quietly
            parser.parse_file(args.execute, quiet=True)
        except FileNotFoundError:
            print(f"Error: File '{args.execute}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error parsing file for execution: {e}")
            sys.exit(1)

        # Create emulator with parsed instructions and initialized components
        emulator = ARM64Emulator(parser.instructions, registers, memory)

        # Set up optional state display callback for showing initial state
        state_callback = None
        if args.registers or args.memory:
            def show_initial_state(emu_obj: ARM64Emulator) -> None:
                """Display initial emulator state before execution begins."""
                if args.registers:
                    print("\nInitial Register State:")
                    emu_obj.registers.display()
                if args.memory:
                    print("\nInitial Stack Memory State:")
                    emu_obj.memory.display()

            state_callback = show_initial_state

        # Execute instructions with specified options
        try:
            steps = emulator.execute(
                trace=args.trace,        # Enable step-by-step tracing
                reset_state=True,        # Start with clean state
                state_callback=state_callback,  # Show initial state if requested
            )
        except Exception as e:
            print(f"Execution error: {e}")
            sys.exit(1)

        # Display execution summary
        print(f"Executed {steps} instruction(s).")
        print(f"Final PC: 0x{emulator.registers.get_pc():016x}")
        print(f"Final SP: 0x{emulator.registers.get_sp():016x}")

        # Show final state if requested
        if args.registers:
            print("\nFinal Register State:")
            emulator.registers.display()

        if args.memory:
            print("\nFinal Stack Memory State:")
            emulator.memory.display()

        return

    # ==================== PARSING MODE ====================
    # Task 1 & 4: Parse assembly file and optionally track PC
    if args.parse:
        # Create parser instance with fresh state
        parser = ARM64Parser()
        
        try:
            # Parse file with optional PC tracking (Task 4)
            # show_pc enables display of program counter progression
            parser.parse_file(args.parse, show_pc=args.pc)
            
            # Display PC summary if tracking was enabled
            if args.pc:
                parser.display_pc_summary()
            
            # Section separator for component states
            print(f"\n{'='*125}")
            print("Component States After Parsing:")
            print('='*125)
            
            # Show registers if requested (usually all zeros after parsing)
            if args.registers:
                print("\nRegister State:")
                print("-"*125)
                parser.registers.display()
            
            # Show memory if requested (should be empty after parsing)
            if args.memory:
                print("\nStack Memory State:")
                print("-"*125)
                parser.memory.display()
                
        except FileNotFoundError:
            print(f"Error: File '{args.parse}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error parsing file: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()