import os
import datetime

class Logger:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.logfile = 'log.txt'
        self.debugfile = 'debug.txt'

        with open(self.logfile, 'w+') as file:
            file.write('Log\n')
        with open(self.debugfile, 'w+') as file:
            file.write('Debug\n')

    def console(self, data):
        print(data)

    def file(self, filename, data):
        if(type(data) != str):
            data = str(data)
        with open(filename, 'a') as file:
            file.write(str(datetime.datetime.now()) + ': ')
            file.write(data)
            file.write('\n')

    def log(self, data, color=''):
        if(type(data) != str):
            data = str(data)

        self.file(self.logfile, data)

        if color == 'red':
            data = f"\033[91m{data}\033[00m"
        elif color == 'green':
            data = f"\033[92m{data}\033[00m"

        if self.verbose: self.console(data)
        
    def debug(self, data):
        self.console(f'Debug: {data}')
        self.file(self.debugfile, data)