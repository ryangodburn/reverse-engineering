import os
import sys
import subprocess
import argparse
from pathlib import Path


# Headless-compatible version of part1.py (without GUI elements)
HEADLESS_SCRIPT_CONTENT = '''
"""
part1_headless.py - Headless version of part1.py
Runs automatically without GUI prompts.
"""

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
    print("Program: {}".format(currentProgram.getName()))
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
        
        print("\\n" + "-" * 60)
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
    
    print("\\n" + "=" * 60)
    print("Total functions decompiled: {}".format(function_count))
    print("=" * 60)


def print_assembly_listing():
    """
    Prints assembly instructions for the entry point and main functions.
    In headless mode, we cannot rely on user selection, so we print
    key areas of the program.
    """
    print("=" * 60)
    print("ASSEMBLY LISTING - KEY FUNCTIONS")
    print("Program: {}".format(currentProgram.getName()))
    print("=" * 60)
    
    # Get the listing
    listing = currentProgram.getListing()
    function_manager = currentProgram.getFunctionManager()
    
    # Get entry point
    entry_point = currentProgram.getImageBase()
    print("\\nImage Base: {}".format(entry_point))
    
    # Find and print assembly for key functions
    key_function_names = ["main", "_main", "Main", "entry", "_start", "WinMain", "_WinMain"]
    
    functions_found = []
    for func in function_manager.getFunctions(True):
        if func.getName() in key_function_names:
            functions_found.append(func)
    
    if not functions_found:
        # If no main found, just get the first few functions
        print("\\n[INFO] No main/entry function found by name. Showing first 3 functions.")
        count = 0
        for func in function_manager.getFunctions(True):
            functions_found.append(func)
            count += 1
            if count >= 3:
                break
    
    for function in functions_found:
        print("\\n" + "-" * 60)
        print("Function: {} at {}".format(function.getName(), function.getEntryPoint()))
        print("-" * 60)
        
        # Get instructions in this function
        addr_set = function.getBody()
        instructions = listing.getInstructions(addr_set, True)
        
        instr_count = 0
        max_instructions = 50  # Limit output
        
        for instruction in instructions:
            # Print instruction details
            addr = instruction.getAddress()
            mnemonic = instruction.getMnemonicString()
            operands = instruction.toString().replace(mnemonic, "").strip()
            
            # Get bytes
            instr_bytes = []
            for i in range(instruction.getLength()):
                byte = getByte(addr.add(i))
                if byte < 0:
                    byte = byte & 0xFF
                instr_bytes.append("{:02X}".format(byte))
            
            print("{}: {:12s} {:20s} ; {}".format(
                addr,
                " ".join(instr_bytes),
                mnemonic,
                operands
            ))
            
            instr_count += 1
            if instr_count >= max_instructions:
                print("... (truncated at {} instructions)".format(max_instructions))
                break
    
    print("\\n" + "=" * 60)


def list_all_functions():
    """
    Lists all functions in the program with their addresses.
    """
    print("=" * 60)
    print("ALL FUNCTIONS IN PROGRAM")
    print("Program: {}".format(currentProgram.getName()))
    print("=" * 60)
    
    function_manager = currentProgram.getFunctionManager()
    
    print("\\n{:<40} {:<20} {}".format("Function Name", "Entry Point", "Size"))
    print("-" * 80)
    
    for function in function_manager.getFunctions(True):
        name = function.getName()
        entry = function.getEntryPoint()
        body = function.getBody()
        size = body.getNumAddresses() if body else 0
        
        print("{:<40} {:<20} {} bytes".format(name, str(entry), size))
    
    print("\\n" + "=" * 60)


def analyze_strings():
    """
    Prints defined strings in the program.
    """
    print("=" * 60)
    print("DEFINED STRINGS IN PROGRAM")
    print("Program: {}".format(currentProgram.getName()))
    print("=" * 60)
    
    listing = currentProgram.getListing()
    data_iterator = listing.getDefinedData(True)
    
    string_count = 0
    
    for data in data_iterator:
        data_type = data.getDataType()
        type_name = data_type.getName().lower()
        
        # Check if it's a string type
        if "string" in type_name or "char[" in type_name:
            value = data.getValue()
            if value is not None:
                # Truncate long strings
                str_val = str(value)
                if len(str_val) > 80:
                    str_val = str_val[:77] + "..."
                print("{}: {}".format(data.getAddress(), str_val))
                string_count += 1
    
    print("\\n" + "-" * 60)
    print("Total strings found: {}".format(string_count))
    print("=" * 60)


def main():
    """
    Main entry point - runs all analysis functions in headless mode.
    """
    print("\\n")
    print("#" * 70)
    print("# HEADLESS ANALYSIS: {}".format(currentProgram.getName()))
    print("#" * 70)
    print("\\n")
    
    # Run all analysis functions
    print("\\n[1/4] Listing all functions...")
    list_all_functions()
    
    print("\\n[2/4] Analyzing strings...")
    analyze_strings()
    
    print("\\n[3/4] Printing assembly for key functions...")
    print_assembly_listing()
    
    print("\\n[4/4] Decompiling all functions...")
    print_all_decompiled_functions()
    
    print("\\n")
    print("#" * 70)
    print("# ANALYSIS COMPLETE: {}".format(currentProgram.getName()))
    print("#" * 70)


# Run the script
main()
'''


def find_ghidra_install():
    """
    Attempts to find the Ghidra installation directory.
    """
    # Check environment variable first
    ghidra_home = os.environ.get('GHIDRA_INSTALL_DIR')
    if ghidra_home and os.path.isdir(ghidra_home):
        return ghidra_home
    
    ghidra_home = os.environ.get('GHIDRA_HOME')
    if ghidra_home and os.path.isdir(ghidra_home):
        return ghidra_home
    
    # If we're in the support directory, go up one level
    script_dir = Path(__file__).resolve().parent
    if script_dir.name == 'support':
        parent = script_dir.parent
        analyze_script = parent / 'support' / 'analyzeHeadless'
        if analyze_script.exists() or (parent / 'support' / 'analyzeHeadless.bat').exists():
            return str(parent)
    
    # Check common installation paths
    common_paths = [
        '/opt/ghidra',
        '/usr/local/ghidra',
        '/usr/share/ghidra',
        os.path.expanduser('~/ghidra'),
    ]
    
    # Look for ghidra_* directories
    for base_path in ['/opt', '/usr/local', os.path.expanduser('~')]:
        if os.path.isdir(base_path):
            try:
                for item in os.listdir(base_path):
                    if item.startswith('ghidra'):
                        full_path = os.path.join(base_path, item)
                        if os.path.isdir(full_path):
                            common_paths.append(full_path)
            except PermissionError:
                pass
    
    for path in common_paths:
        if os.path.isdir(path):
            analyze_script = os.path.join(path, 'support', 'analyzeHeadless')
            if os.path.exists(analyze_script) or os.path.exists(analyze_script + '.bat'):
                return path
    
    return None


def get_analyze_headless_path(ghidra_install):
    """
    Returns the path to the analyzeHeadless script.
    """
    support_dir = os.path.join(ghidra_install, 'support')
    
    if sys.platform == 'win32':
        return os.path.join(support_dir, 'analyzeHeadless.bat')
    else:
        return os.path.join(support_dir, 'analyzeHeadless')


def is_executable_file(filepath):
    """
    Determines if a file is likely an executable based on extension or magic bytes.
    """
    # Common executable extensions
    executable_extensions = {
        '.exe', '.dll', '.so', '.dylib', '.bin', '.elf',
        '.o', '.obj', '.com', '.sys', '.drv', '.ocx',
        '.axf', '.prx', '.puff', '.ko', '.mod'
    }
    
    path = Path(filepath)
    
    # Check extension
    if path.suffix.lower() in executable_extensions:
        return True
    
    # Check for no extension (common for Linux binaries)
    if path.suffix == '':
        try:
            with open(filepath, 'rb') as f:
                magic = f.read(4)
                # ELF magic: 0x7f ELF
                if magic[:4] == b'\x7fELF':
                    return True
                # PE magic: MZ
                if magic[:2] == b'MZ':
                    return True
                # Mach-O magic
                if magic[:4] in [b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf',
                                  b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe']:
                    return True
        except (IOError, PermissionError):
            pass
    
    return False


def find_programs_in_directory(directory):
    """
    Finds all executable programs in the specified directory.
    """
    programs = []
    
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise ValueError(f"Not a valid directory: {directory}")
    
    for item in dir_path.iterdir():
        if item.is_file() and is_executable_file(str(item)):
            programs.append(str(item))
    
    return sorted(programs)


def run_headless_analysis(ghidra_install, program_path, script_path, project_dir, project_name):
    """
    Runs Ghidra headless analyzer on a single program.
    """
    analyze_headless = get_analyze_headless_path(ghidra_install)
    
    if not os.path.exists(analyze_headless):
        raise FileNotFoundError(f"analyzeHeadless not found at: {analyze_headless}")
    
    # Build the command
    cmd = [
        analyze_headless,
        project_dir,
        project_name,
        '-import', program_path,
        '-postScript', script_path,
        '-overwrite',  # Overwrite if already exists
    ]
    
    print(f"\nRunning: {' '.join(cmd)}\n")
    
    result = subprocess.run(
        cmd,
        capture_output=False,
        text=True
    )
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description='Run Ghidra headless analysis on all programs in a directory'
    )
    parser.add_argument(
        'directory',
        help='Directory containing programs to analyze'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output directory for Ghidra project (default: ./ghidra_headless_project)',
        default='./ghidra_headless_project'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate directory
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a valid directory")
        sys.exit(1)
    
    # Find Ghidra installation
    ghidra_install = find_ghidra_install()
    if ghidra_install is None:
        print("Error: Could not find Ghidra installation.")
        print("\nPlease set the GHIDRA_INSTALL_DIR environment variable:")
        print("  Linux/Mac: export GHIDRA_INSTALL_DIR=/path/to/ghidra")
        print("  Windows:   set GHIDRA_INSTALL_DIR=C:\\path\\to\\ghidra")
        sys.exit(1)
    
    print("=" * 70)
    print("GHIDRA HEADLESS BATCH ANALYZER")
    print("=" * 70)
    print(f"Ghidra Installation: {ghidra_install}")
    print(f"Target Directory:    {args.directory}")
    print(f"Project Directory:   {args.output}")
    print("=" * 70)
    
    # Find all programs in the directory
    programs = find_programs_in_directory(args.directory)
    
    if not programs:
        print(f"\nNo executable programs found in '{args.directory}'")
        print("Supported formats: EXE, DLL, ELF, Mach-O, and other binary formats")
        sys.exit(1)
    
    print(f"\nFound {len(programs)} program(s) to analyze:")
    for prog in programs:
        print(f"  - {os.path.basename(prog)}")
    print()
    
    # Create project directory
    project_dir = os.path.abspath(args.output)
    os.makedirs(project_dir, exist_ok=True)
    
    # Create the headless script in the same directory as this script
    script_dir = Path(__file__).resolve().parent
    headless_script_path = script_dir / 'part1_headless.py'
    
    # Write the headless script
    with open(headless_script_path, 'w') as f:
        f.write(HEADLESS_SCRIPT_CONTENT)
    
    print(f"Created headless script: {headless_script_path}")
    
    # Process each program
    results = {}
    
    for i, program_path in enumerate(programs, 1):
        program_name = os.path.basename(program_path)
        project_name = f"Analysis_{i}"
        
        print("\n" + "=" * 70)
        print(f"[{i}/{len(programs)}] Analyzing: {program_name}")
        print("=" * 70)
        
        try:
            result = run_headless_analysis(
                ghidra_install=ghidra_install,
                program_path=program_path,
                script_path=str(headless_script_path),
                project_dir=project_dir,
                project_name=project_name
            )
            
            results[program_name] = {
                'success': result.returncode == 0,
                'return_code': result.returncode
            }
            
            if result.returncode == 0:
                print(f"\n[SUCCESS] Analysis completed for {program_name}")
            else:
                print(f"\n[WARNING] Analysis completed with return code {result.returncode}")
                
        except Exception as e:
            print(f"\n[ERROR] Failed to analyze {program_name}: {e}")
            results[program_name] = {
                'success': False,
                'error': str(e)
            }
    
    # Print summary
    print("\n" + "=" * 70)
    print("ANALYSIS SUMMARY")
    print("=" * 70)
    
    success_count = sum(1 for r in results.values() if r.get('success', False))
    print(f"Total programs: {len(programs)}")
    print(f"Successful:     {success_count}")
    print(f"Failed:         {len(programs) - success_count}")
    
    print("\nDetailed Results:")
    for program, result in results.items():
        status = "SUCCESS" if result.get('success', False) else "FAILED"
        print(f"  {program}: {status}")
        if 'error' in result:
            print(f"    Error: {result['error']}")
    
    print("\n" + "=" * 70)
    print(f"Project files saved to: {project_dir}")
    print("=" * 70)
    
    print(f"\nHeadless script available at: {headless_script_path}")
    
    # Exit with appropriate code
    if success_count == len(programs):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
