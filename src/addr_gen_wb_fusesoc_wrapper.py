#!/usr/bin/python3

import os
import sys
import yaml
import subprocess

if __name__ == "__main__":

    with open(sys.argv[1], 'r') as config_file:
        try:
            config = yaml.safe_load(config_file)
        except yaml.YAMLError as exc:
            print(exc)

    files_root = config['files_root'] + "/"

    try:
        infile = files_root + config['parameters']['infile']
    except:
        print("ERROR: Input .xml file (infile parameter) needs to be specified!")
        sys.exit(1)
    try:
        hdl = files_root + config['parameters']['hdl']
    except:
        # If path for HDL files is not specified generate them in FuseSoc cache.
        hdl = "."

    args = ['python3', os.path.dirname(__file__) + '/addr_gen_wb.py',
            '--fusesoc',
            '--fusesoc_vlnv', config['vlnv'],
            '--infile', infile,
            '--hdl', hdl]

    try:
        amapxml = str(config['parameters']['amapxml'])
        args += ['--amapxml', files_root + amapxml]
    except:
        pass
    try:
        ipbus = str(config['parameters']['ipbus'])
        args += ['--ipbus', files_root + ipbus]
    except:
        pass
    try:
        header = str(config['parameters']['header'])
        args += ['--header', files_root + header]
    except:
        pass
    try:
        fs = str(config['parameters']['fs'])
        args += ['--fs', files_root + fs]
    except:
        pass
    try:
        python = str(config['parameters']['python'])
        args += ['--python', files_root + python]
    except:
        pass
    try:
        pythondca = str(config['parameters']['pythondca'])
        args += ['--pythondca', files_root + pythondca]
    except:
        pass
    try:
        html = str(config['parameters']['html'])
        args += ['--html', files_root + html]
    except:
        pass

    ret = subprocess.run(args)
    if ret.returncode != 0:
        exit(ret.returncode)
