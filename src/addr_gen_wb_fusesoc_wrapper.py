#!/usr/bin/python3

import os
import sys
import yaml
import subprocess

if __name__ == "__main__":

    print(sys.argv)

    with open(sys.argv[1], 'r') as config_file:
        try:
            config = yaml.safe_load(config_file)
            print(config)
        except yaml.YAMLError as exc:
            print(exc)

    try:
        infile = config['files_root'] + "/" + config['parameters']['infile']
    except:
        print("ERROR: Input .xml file (infile parameter) needs to be specified!")
        sys.exit(1)
    try:
        hdl = config['parameters']['hdl']
    except:
        print("ERROR: Path for HDL files (hdl parameter) needs to be specified!")
        sys.exit(1)

    args = ['python', os.path.dirname(__file__) + '/addr_gen_wb.py',
            '--fusesoc',
            '--fusesoc_vlnv', config['vlnv'],
            '--infile', infile,
            '--hdl', hdl]

    try:
        ipbus = str(config['parameters']['ipbus'])
        args += ['--ipbus', ipbus]
    except:
        pass
    try:
        header = str(config['parameters']['header'])
        args += ['--header', header]
    except:
        pass
    try:
        fs = str(config['parameters']['fs'])
        args += ['--fs', fs]
    except:
        pass
    try:
        python = str(config['parameters']['python'])
        args += ['--python', python]
    except:
        pass
    try:
        html = str(config['parameters']['html'])
        args += ['--html', html]
    except:
        pass

    print(args)
    subprocess.run(args)
