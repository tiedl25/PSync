# PSync
This is an implementation of rclone and watchdog (python module) to perform file syncing between local and remote filesystems by monitoring the local file changes. 
It is currently only supported under linux and only tested with GoogleDrive and OneDrive.

Hidden files are excluded. The backsync from remote to local takes place every 5 minutes, but can also be changed with a commandline argument.
The fallback implementation that this is refering to takes place for all currently supported rclone remotes. The only exception is GoogleDrive, with a native implementation of it's API. Other remotes may be following in the future, but this is not guaranteed. Also there exist other tools that can do that probably better. 

Currently under active development
