# Files & Directories

*From The Linux Command Line, chapter 4*

## Wildcards (work with any command)

* `*` → any characters        `*.log` → all .log files
* `?` → exactly one character `file?.txt` → file1.txt, fileA.txt
* `[abc]` → one of these      `file[12].txt` → file1.txt, file2.txt
* `{a,b}` → each of these     `*.{log,md}` → all .log and .md files
* Test a wildcard safely first: `ls *.log` before `rm *.log`

## Creating

* `touch file.txt` → Creates an empty file or updates its timestamps.
* `mkdir dir` → Creates a directory.
* `mkdir dir1 dir2` → Creates several at once.
* `mkdir -p dir1/dir2` → Creates parent directories if they don't exist.

## Copying

* `cp source destination` → Copies a file.
* `cp -r source_dir destination_dir` → Recursively copies a directory and its contents.
* `cp -i` → Asks before overwriting.
* `cp -v` → Shows what is being copied.
* `cp -a` → Archive: keeps permissions, owner, timestamps (use for backups).

## Moving & Renaming

* `mv source destination` → Moves a file/directory.
* `mv old.txt new.txt` → Renames a file.
* `mv file.txt /tmp/` → Moves a file to another directory.
* `mv -i` → Asks before overwriting.
* `mv` is used for both moving and renaming.

## Deleting

* `rm file.txt` → Removes a file.
* `rm -i file.txt` → Asks before deleting.
* `rm -r directory` → Recursively removes a directory and its contents.
* `rmdir directory` → Removes an empty directory only.
* `rm -f file.txt` → Forcefully removes a file without prompting.
* `rm -rf directory` → Forcefully and recursively removes a directory.
* `rm` permanently removes files; there is no recycle bin.

## Links

* Inode → the number identifying where a file's data actually lives; see it with `ls -li`.
* Hard link → `ln file hardlink`
    * A second name for the same data (same inode number).
    * Deleting the original does not delete the data; it's gone only when the last name is removed.
    * Can't point to a directory or across disks/filesystems.
* Soft (symbolic) link → `ln -s file softlink`
    * A note pointing to the file's name (its own inode).
    * Breaks if the original is deleted.
    * Can point to directories and across disks.
* `ln -sfn target link` → replace an existing link to a folder.

## Related (other chapters)

* `find` → Searches for files/directories based on criteria ([ch 17](finding-files.md)).
* `locate` → Searches for files using a pre-built database ([ch 17](finding-files.md)).
* `which command` → Shows the executable path of a command ([ch 5](working-with-commands.md)).

!!! question "Interview points"

    * `cp` → Copy | `mv` → Move/Rename | `rm` → Remove
    * `mkdir` → Create directory | `touch` → Create file / update timestamps
    * `find` → Search filesystem
    * Hard vs soft link: hard shares the inode and survives deleting the original;
      soft has its own inode, can cross disks and point to dirs, and breaks if the target is deleted.

!!! warning "rm -rf"

    `rm -rf` is powerful and dangerous. In production, always verify the path
    before executing it (run `ls` on the same path first).
