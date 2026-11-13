from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model.symbol import SourceType

def print_all_decompiled_functions():
    """
    Prints decompiled code for each function within the program.
    Uses Ghidra's DecompInterface to decompile each function.
    """
    print("=" * 60)
    print("DECOMPILED CODE FOR ALL FUNCTIONS")
    print("=" * 60)
    
    # Initialize the decompiler
    decompiler = DecompInterface()
    decompiler.openProgram(currentProgram)
    
    # Get the function manager
    function_manager = currentProgram.getFunctionManager()
    
    # Get all functions in the program
    functions = function_manager.getFunctions(True)  # True = forward iteration
    
    # Create a task monitor for progress
    monitor = ConsoleTaskMonitor()
    
    function_count = 0
    
    for function in functions:
        function_count += 1
        
        print("\n" + "-" * 60)
        print("Function: {} (Address: {})".format(
            function.getName(), 
            function.getEntryPoint()
        ))
        print("-" * 60)
        
        # Decompile the function
        try:
            results = decompiler.decompileFunction(function, 30, monitor)
            
            if results is not None and results.decompileCompleted():
                # Get the decompiled C code
                decomp_function = results.getDecompiledFunction()
                if decomp_function is not None:
                    c_code = decomp_function.getC()
                    print(c_code)
                else:
                    print("[ERROR] Could not get decompiled function")
            else:
                error_msg = results.getErrorMessage() if results else "Unknown error"
                print("[ERROR] Decompilation failed: {}".format(error_msg))
                
        except Exception as e:
            print("[ERROR] Exception during decompilation: {}".format(str(e)))
    
    # Clean up
    decompiler.dispose()
    
    print("\n" + "=" * 60)
    print("Total functions decompiled: {}".format(function_count))
    print("=" * 60)


def print_assembly_at_selected_address():
    """
    Prints the assembly instruction at the current user selected address.
    The selected address is what the user has clicked on in the Listing view.
    """
    print("=" * 60)
    print("ASSEMBLY AT SELECTED ADDRESS")
    print("=" * 60)
    
    # Get the current address (what the user has selected/clicked on)
    selected_address = currentAddress
    
    if selected_address is None:
        print("[ERROR] No address is currently selected.")
        print("Please click on an address in the Listing view and run again.")
        return
    
    print("Selected Address: {}".format(selected_address))
    print("-" * 60)
    
    # Get the listing (contains instructions and data)
    listing = currentProgram.getListing()
    
    # Get the instruction at the selected address
    instruction = listing.getInstructionAt(selected_address)
    
    if instruction is not None:
        # Print instruction details
        print("Mnemonic:      {}".format(instruction.getMnemonicString()))
        print("Full Instruction: {}".format(instruction.toString()))
        print("Address:       {}".format(instruction.getAddress()))
        print("Length:        {} bytes".format(instruction.getLength()))
        
        # Get the bytes of the instruction
        instr_bytes = []
        for i in range(instruction.getLength()):
            byte = getByte(instruction.getAddress().add(i))
            if byte < 0:
                byte = byte & 0xFF
            instr_bytes.append("{:02X}".format(byte))
        print("Bytes:         {}".format(" ".join(instr_bytes)))
        
        # Get number of operands
        num_operands = instruction.getNumOperands()
        print("Num Operands:  {}".format(num_operands))
        
        # Print each operand
        for i in range(num_operands):
            operand = instruction.getDefaultOperandRepresentation(i)
            print("  Operand {}: {}".format(i, operand))
        
        # Check if this instruction is in a function
        function = getFunctionContaining(selected_address)
        if function is not None:
            print("In Function:   {} (at {})".format(
                function.getName(), 
                function.getEntryPoint()
            ))
        else:
            print("In Function:   (not in a function)")
            
    else:
        # Maybe it's data, not an instruction
        data = listing.getDataAt(selected_address)
        if data is not None:
            print("[INFO] This address contains data, not an instruction.")
            print("Data Type:     {}".format(data.getDataType().getName()))
            print("Data Value:    {}".format(data.getValue()))
        else:
            print("[ERROR] No instruction or defined data at this address.")
            # Try to show the raw bytes anyway
            print("Raw byte at address: {:02X}".format(getByte(selected_address) & 0xFF))
    
    print("=" * 60)


def rename_main_function():
    """
    Renames the main() function to a string the user enters via GUI prompt.
    Uses Ghidra's askString() to prompt the user for the new name.
    """
    print("=" * 60)
    print("RENAME MAIN FUNCTION")
    print("=" * 60)
    
    # Get the function manager
    function_manager = currentProgram.getFunctionManager()
    
    # Find the main function
    # Try multiple common names for main
    main_function = None
    main_names = ["main", "_main", "Main", "MAIN", "WinMain", "_WinMain", "entry"]
    
    for name in main_names:
        # Search by name
        functions = list(function_manager.getFunctions(True))
        for func in functions:
            if func.getName() == name:
                main_function = func
                break
        if main_function:
            break
    
    # If not found by name, try to find by symbol
    if main_function is None:
        symbol_table = currentProgram.getSymbolTable()
        for name in main_names:
            symbols = symbol_table.getSymbols(name)
            for symbol in symbols:
                addr = symbol.getAddress()
                func = function_manager.getFunctionAt(addr)
                if func is not None:
                    main_function = func
                    break
            if main_function:
                break
    
    if main_function is None:
        print("[ERROR] Could not find main() function.")
        print("Searched for: {}".format(", ".join(main_names)))
        
        # List all functions to help user find it
        print("\nAvailable functions (first 20):")
        count = 0
        for func in function_manager.getFunctions(True):
            print("  - {} at {}".format(func.getName(), func.getEntryPoint()))
            count += 1
            if count >= 20:
                print("  ... (more functions exist)")
                break
        return
    
    print("Found main function: {} at {}".format(
        main_function.getName(), 
        main_function.getEntryPoint()
    ))
    
    # Prompt user for new name using GUI dialog
    try:
        new_name = askString(
            "Rename Main Function",           # Dialog title
            "Enter new name for main():",     # Prompt message
            main_function.getName()           # Default value
        )
        
        if new_name is None or new_name.strip() == "":
            print("[CANCELLED] No name entered, function not renamed.")
            return
        
        new_name = new_name.strip()
        
        # Validate the new name (basic check for valid identifier)
        if not new_name[0].isalpha() and new_name[0] != '_':
            print("[ERROR] Function name must start with a letter or underscore.")
            return
        
        # Store old name for confirmation message
        old_name = main_function.getName()
        
        # Rename the function
        main_function.setName(new_name, SourceType.USER_DEFINED)
        
        print("[SUCCESS] Function renamed!")
        print("  Old name: {}".format(old_name))
        print("  New name: {}".format(new_name))
        print("  Address:  {}".format(main_function.getEntryPoint()))
        
    except ghidra.util.exception.DuplicateNameException as e:
        print("[ERROR] A function with that name already exists: {}".format(str(e)))
    except ghidra.util.exception.InvalidInputException as e:
        print("[ERROR] Invalid function name: {}".format(str(e)))
    except Exception as e:
        # User cancelled the dialog
        if "cancel" in str(e).lower():
            print("[CANCELLED] User cancelled the operation.")
        else:
            print("[ERROR] Failed to rename function: {}".format(str(e)))
    
    print("=" * 60)


def show_menu():
    """
    Shows a menu for the user to select which function to run.
    """
    print("\n" + "=" * 60)
    print("PYGHIDRA UTILITY SCRIPT")
    print("=" * 60)
    print("1. Print decompiled code for all functions")
    print("2. Print assembly instruction at selected address")
    print("3. Rename main() function")
    print("4. Run all (1, 2, and 3)")
    print("=" * 60)
    
    try:
        choice = askChoice(
            "PyGhidra Utility",
            "Select an operation:",
            [
                "1. Print decompiled code for all functions",
                "2. Print assembly at selected address",
                "3. Rename main() function",
                "4. Run all operations"
            ],
            "1. Print decompiled code for all functions"
        )
        
        if "1." in choice:
            print_all_decompiled_functions()
        elif "2." in choice:
            print_assembly_at_selected_address()
        elif "3." in choice:
            rename_main_function()
        elif "4." in choice:
            print_all_decompiled_functions()
            print("\n\n")
            print_assembly_at_selected_address()
            print("\n\n")
            rename_main_function()
        else:
            print("[INFO] No valid option selected.")
            
    except Exception as e:
        if "cancel" in str(e).lower():
            print("[CANCELLED] User cancelled the operation.")
        else:
            print("[ERROR] {}".format(str(e)))
            # If GUI fails, run all by default
            print("[INFO] Running all functions...")
            print_all_decompiled_functions()
            print("\n\n")
            print_assembly_at_selected_address()
            print("\n\n")
            rename_main_function()


def main():
    """
    Main entry point for the script.
    """
    show_menu()


# Run the script
if __name__ == "__main__":
    main()
else:
    # When run from Ghidra Script Manager
    main()