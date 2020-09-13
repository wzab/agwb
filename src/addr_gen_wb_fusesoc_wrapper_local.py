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
    
    args = ['python3', os.path.dirname(__file__) + '/addr_gen_wb.py',
            '--fusesoc',
            '--fusesoc_vlnv', config['vlnv'],
            '--infile', infile]
    
    try:
        hdl = files_root + config['parameters']['hdl']
        args += ['--hdl', hdl]
        os.makedirs(hdl)
    except:
        pass
        
    try:
        ipbus = files_root + str(config['parameters']['ipbus'])
        args += ['--ipbus', ipbus]
        os.makedirs(ipbus)
    except:
        pass
    
    try:
        header = files_root + str(config['parameters']['header'])
        args += ['--header', header]
        os.makedirs(header)
    except:
        pass

    try:
        fs = files_root + str(config['parameters']['fs'])
        args += ['--fs', fs]
        os.makedirs(fs)
    except:
        pass

    try:
        python = files_root + str(config['parameters']['python'])
        args += ['--python', python]
        os.makedirs(python)
    except:
        pass
    
    try:
        html = files_root + config['parameters']['html']
        args += ['--html', html]
        os.makedirs(html)
    except:
        pass

    subprocess.run(args)
