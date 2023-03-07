# PSync

This is an implementation of rclone and the python module watchdog to perform file syncing between local and remote filesystems by monitoring the local file changes. 
It is currently only supported under linux and only tested with GoogleDrive and OneDrive.

The backsync from remote to local takes place every 5 minutes, but can also be changed.
The fallback implementation that this is refering to takes place for all currently supported rclone remotes. The only exception is GoogleDrive, with a native implementation of it's API. Other remotes may be following in the future, but this is not guaranteed. Also there exist other tools that can do that probably better.

## Installation
Via the python package manager: `pip install -i https://test.pypi.org/simple/ psync` <br />
Be sure to install the latest release. Check https://test.pypi.org/project/psync/ and specify with `psync==version number`.

## Usage
To use this cli, one has to first setup a remote via rclone. After that it can be used within psync. The cli uses a similar command scheme to rclone, where remote paths are specified by the name of the remote followed by a colon and the folder path of the remote folder. Local folders are simply specified by there whole path. 
* As before said the backsync takes place every 5 minutes. This can be changed with `--every-minutes` or `-e`. 
* For the first launch one should use the `--init`/`-i` parameter. This performs a local -> remote sync and if necessary mirrors the whole folder to the drive. * For resyncinc purposes the `--resync`/`-r` parameter can be used, that uses the rclone bisync command under the hood. 
* And for general day to day use one should be definitely take advantage of the `--backsync`/`-b` parameter, that performs a remote -> local sync initially to keep everything up-to-date.
* For more invormation about the changes use the `--verbose`/`-v` parameter.

The script detects if you're using a GoogleDrive remote and switches to the native implementation instead of the default one. The periodic backsyncing is therefore disabled.

Currently under active development
