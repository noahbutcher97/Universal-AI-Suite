:; if [ -z "$BASH_VERSION" ]; then echo "Please run this script with bash: bash launch.cmd"; exit 1; fi
:; # The above line is a valid label in Windows (ignored) and a check in Bash.
:; 
:; # --- UNIX / MAC / LINUX START ---
:; echo "Detected Unix-like Environment."
:; chmod +x ./bin/boot_unix.sh
:; ./bin/boot_unix.sh
:; exit $?
:; # --- UNIX END ---

@ECHO OFF
:: --- WINDOWS START ---
ECHO Detected Windows Environment.
CALL bin\boot_windows.bat
EXIT /B %ERRORLEVEL%
:: --- WINDOWS END ---
