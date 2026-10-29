# Navigation

*From The Linux Command Line, chapter 2*

* Navigation → Moving through the Linux filesystem hierarchy using shell commands.
* Linux uses a hierarchical filesystem with `/` as the root directory.

## Important Commands

* `pwd` → Print Working Directory; displays the current directory.
* `ls` → Lists files and directories in the current directory.
* `ls -la` → Lists all files, including hidden files, with detailed information.
* `cd` → Change Directory; moves to another directory.
* `cd ..` → Moves to the parent directory.
* `cd ~` or just `cd` → Moves to the user's home directory.
* `cd -` → Moves back to the previous directory.
* `cd /` → Moves to the root directory.

## Paths

* Absolute path → Full path starting from `/`.
    * Example: `/home/aditya/Documents`
* Relative path → Path relative to the current working directory.
    * Example: `Documents/file.txt`
* `.` → Current directory.
* `..` → Parent directory.
* `~` → Current user's home directory.

## Filename rules

* Hidden files start with `.` (e.g. `.bashrc`); plain `ls` doesn't show them.
* Filenames are case-sensitive: `File1` ≠ `file1`.
* Avoid spaces in names; use `_` or `-`.
* Extensions don't matter to Linux; `.txt` is just part of the name.

!!! question "Interview point"

    Absolute paths are independent of the current working directory; relative paths depend on it.
