# CSCI 4448: Reverse Engineering

Coursework from **CSCI 4448: Reverse Engineering** at the **University of New Haven**, Fall 2025 (fourth year, fall semester).

- **Author:** Ryan Godburn
- **Partner:** Arjun Aravind (ARM64 emulator and WannaCry report)
- **Languages and tools:** Python 3, Ghidra (scripting and headless mode), x32dbg

No executables or malware samples are included in this repository: only the scripts, the emulator and the written report.

## ARM64 Emulator (`ARM64 Emulator/`)

An educational emulator, written in Python with no external dependencies, for a subset of 64-bit ARM. It reads disassembler-style listings (`address: machine_code  instruction`), then parses or executes them while tracking registers, flags and a 256-byte stack.

- **Instructions:** `ADD`, `SUB`, `MUL`, `AND`, `EOR`, `MOV`, `LDR`/`LDRB`, `STR`/`STRB`, `CMP`, `B`, `B.GT`, `B.LE`, `RET`, `NOP`
- **Registers:** `X0`–`X30`, their 32-bit `W` views, `XZR`/`WZR`, `SP`, `PC`
- **Options:** parse only, execute, step-by-step trace, and register and stack dumps

```bash
cd "ARM64 Emulator"
python3 main.py -x test1.txt --trace     # run with a trace of every instruction
python3 main.py -x test2.txt -r -m       # run, then show registers and stack memory
```

`readme.txt` has the full option list, and `test1.txt`–`test5.txt` are sample programs.

## Ghidra scripting

| File | What it does |
| --- | --- |
| `part1.py` | Ghidra script that prints the decompiled C for every function in the open program. |
| `headless.py` | Batch version of part 1: runs Ghidra's headless analyzer over every program in a folder and prints the decompiled code, assembly listing, function list and strings for each. Usage: `python3 headless.py <folder>`. |
| `part2.py` | Ghidra script that solves two stages of a CTF-style challenge binary: it reads two encoded strings from the program's memory and undoes a Caesar shift (stage 2) and Base64 encoding (stage 3) to recover the passwords. |
| `part3.py` | Runs `part2.py` against the challenge binary (`main.exe`, not included) with Ghidra's headless analyzer. |
| `genkeys.py` | Key generator for a `keygenme.exe` crackme. Reversing its check showed a valid key is 16 characters whose byte-wise XOR plus signed byte sum equals `0xD8` (mod 256); the script generates and validates such keys. |

The headless scripts find Ghidra through the `GHIDRA_INSTALL_DIR` (or `GHIDRA_HOME`) environment variable or a standard install location.

## Reversing WannaCry (`Reversing WannaCry.pdf`)

*With Arjun Aravind · December 2025 · 19 pages*

A malware analysis report on a WannaCry ransomware sample:

- File size, hashes and VirusTotal detection results.
- Static analysis in Ghidra of the kill-switch logic: the sample checks a hard-coded domain and stops if it can reach it.
- Dynamic analysis in x32dbg confirming the kill-switch URL, extracting the embedded payload with Resource Hacker, and observing its RSA-2048 (Windows CryptoAPI) and AES encryption.

---

*Archived coursework, shared as part of my portfolio. If you're taking this course now, please follow your instructor's academic integrity policy.*
