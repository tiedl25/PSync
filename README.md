# PSync
Implementation of Rclone and Inotify to perform file syncing between local and remote by monitoring file changes. 
It can be only used under linux because the inotify dependency and is currently only tested on GoogleDrive. 

Hidden files are excluded. The backsync from remote to local takes place every 5 minutes, but can also be changed with a commandline argument.

Currently under active development
