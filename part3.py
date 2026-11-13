import os
import sys
import subprocess
import shutil
import tempfile
from pathlib import Path


def find_ghidra_install():
    """
    Attempts to find the Ghidra installation directory.
    Checks environment variable first, then common installation paths.
    """
    # Check environment variable first
    ghidra_home = os.environ.get('GHIDRA_INSTALL_DIR')
    if ghidra_home and os.path.isdir(ghidra_home):
        return ghidra_home
    
    # Also check GHIDRA_HOME
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
        os.path.expanduser('~/tools/ghidra'),
        'C:\\ghidra',
        'C:\\Program Files\\ghidra',
    ]
    
    # Also look for ghidra_* directories
    for base_path in ['/opt', '/usr/local', os.path.expanduser('~')]:
        if os.path.isdir(base_path):
            for item in os.listdir(base_path):
                if item.startswith('ghidra'):
                    full_path = os.path.join(base_path, item)
                    if os.path.isdir(full_path):
                        common_paths.append(full_path)
    
    for path in common_paths:
        if os.path.isdir(path):
            # Verify it's a valid Ghidra installation by checking for analyzeHeadless
            analyze_script = os.path.join(path, 'support', 'analyzeHeadless')
            if os.path.exists(analyze_script) or os.path.exists(analyze_script + '.bat'):
                return path
    
    return None


def get_analyze_headless_path(ghidra_install):
    """
    Returns the path to the analyzeHeadless script based on the OS.
    """
    support_dir = os.path.join(ghidra_install, 'support')
    
    if sys.platform == 'win32':
        return os.path.join(support_dir, 'analyzeHeadless.bat')
    else:
        return os.path.join(support_dir, 'analyzeHeadless')


def run_headless_analysis(ghidra_install, main_exe_path, script_path, project_dir=None):
    """
    Runs Ghidra's headless analyzer to:
    1. Create a new project
    2. Import main.exe
    3. Run part2.py as a post-analysis script
    
    Args:
        ghidra_install: Path to Ghidra installation directory
        main_exe_path: Path to main.exe file
        script_path: Path to part2.py script
        project_dir: Optional directory for the Ghidra project (uses temp dir if not specified)
    
    Returns:
        subprocess.CompletedProcess result
    """
    analyze_headless = get_analyze_headless_path(ghidra_install)
    
    if not os.path.exists(analyze_headless):
        raise FileNotFoundError(f"analyzeHeadless not found at: {analyze_headless}")
    
    # Create project directory if not specified
    if project_dir is None:
        project_dir = tempfile.mkdtemp(prefix='ghidra_ctf_')
        cleanup_project = True
    else:
        os.makedirs(project_dir, exist_ok=True)
        cleanup_project = False
    
    project_name = "CTF_Analysis"
    
    # Build the command
    # Format: analyzeHeadless <project_location> <project_name> -import <file> -postScript <script>
    cmd = [
        analyze_headless,
        project_dir,
        project_name,
        '-import', main_exe_path,
        '-postScript', script_path,
        '-scriptlog', os.path.join(project_dir, 'script.log'),
    ]
    
    print("=" * 60)
    print("Ghidra Headless Analysis")
    print("=" * 60)
    print(f"Ghidra Installation: {ghidra_install}")
    print(f"Project Directory:   {project_dir}")
    print(f"Project Name:        {project_name}")
    print(f"Target Binary:       {main_exe_path}")
    print(f"Analysis Script:     {script_path}")
    print("=" * 60)
    print("\nRunning command:")
    print(" ".join(cmd))
    print("\n" + "-" * 60)
    print("Ghidra Output:")
    print("-" * 60 + "\n")
    
    try:
        # Run the headless analyzer
        result = subprocess.run(
            cmd,
            capture_output=False,  # Let output go to stdout/stderr
            text=True,
            cwd=os.path.dirname(main_exe_path) if os.path.dirname(main_exe_path) else None
        )
        
        print("\n" + "-" * 60)
        print(f"Analysis completed with return code: {result.returncode}")
        
        # Check for script log
        script_log = os.path.join(project_dir, 'script.log')
        if os.path.exists(script_log):
            print("\n" + "=" * 60)
            print("Script Log Contents:")
            print("=" * 60)
            with open(script_log, 'r') as f:
                print(f.read())
        
        return result
        
    except Exception as e:
        print(f"Error running headless analysis: {e}")
        raise
    finally:
        # Optionally clean up the project directory
        if cleanup_project and os.path.exists(project_dir):
            print(f"\nNote: Temporary project directory at: {project_dir}")
            print("You may delete it manually when done.")
            # Uncomment the following to auto-cleanup:
            # shutil.rmtree(project_dir, ignore_errors=True)


def main():
    """
    Main entry point for the script.
    """
    # Determine the directory where this script is located
    script_dir = Path(__file__).resolve().parent
    
    # Paths to main.exe and part2.py (in the same directory as this script)
    main_exe_path = script_dir / 'main.exe'
    part2_script_path = script_dir / 'part2.py'
    
    # Validate that required files exist
    if not main_exe_path.exists():
        print(f"Error: main.exe not found at: {main_exe_path}")
        print("Please ensure main.exe is in the same directory as this script.")
        sys.exit(1)
    
    if not part2_script_path.exists():
        print(f"Error: part2.py not found at: {part2_script_path}")
        print("Please ensure part2.py is in the same directory as this script.")
        sys.exit(1)
    
    # Find Ghidra installation
    ghidra_install = find_ghidra_install()
    
    if ghidra_install is None:
        print("Error: Could not find Ghidra installation.")
        print("\nPlease set the GHIDRA_INSTALL_DIR environment variable:")
        print("  Linux/Mac: export GHIDRA_INSTALL_DIR=/path/to/ghidra")
        print("  Windows:   set GHIDRA_INSTALL_DIR=C:\\path\\to\\ghidra")
        print("\nOr ensure Ghidra is installed in a standard location.")
        sys.exit(1)
    
    # Create a project directory in the current working directory
    project_dir = script_dir / 'ghidra_project'
    
    try:
        result = run_headless_analysis(
            ghidra_install=ghidra_install,
            main_exe_path=str(main_exe_path),
            script_path=str(part2_script_path),
            project_dir=str(project_dir)
        )
        
        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("SUCCESS: Analysis completed successfully!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print(f"WARNING: Analysis completed with return code {result.returncode}")
            print("Check the output above for any errors.")
            print("=" * 60)
            sys.exit(result.returncode)
            
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\nError running Ghidra: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()