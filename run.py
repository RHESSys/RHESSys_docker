#!/usr/bin/env python

'''
To run:

SRC_VOLUME=/tmp DATA_VOLUME=/tmp UUID=1345f6b3a46e RID=MYRESOURCE123 RHESSYS_PROJECT=DR5_3m_nonburned_DEM_rain_duration_DEM_float_lctest RHESSYS_PARAMS="-st 2001 1 1 1 -ed 2001 1 2 1 -b -t tecfiles/tec_daily.txt -w worldfiles/world_init -r flow/world_init_res_conn_subsurface.flow flow/world_init_res_conn_surface.flow -s 1.43092108352 3.81468111311 3.04983096856 -sv 2.35626069137 49.1712407611 -gw 0.00353233818322 0.495935816914" RHESSYS_USE_SRC_FROM_DATA=True ./run.py
'''

import os
import sys
from subprocess import *
import re

MAKE_PATH = '/usr/bin/make'

def main():
    # Read environment
    src_vol = os.environ['SRC_VOLUME']
    data_vol = os.environ['DATA_VOLUME']
    rsrc_id = os.environ['RID']
    run_id = os.environ['UUID']
    results_url = os.environ['RESULTS_URL']
    
    if os.environ.has_key('RHESSYS_USE_SRC_FROM_DATA'):
        use_src_from_data_vol = bool(os.environ['RHESSYS_USE_SRC_FROM_DATA'])
    else:
        use_src_from_data_vol = False
    rhessys_project = os.environ['RHESSYS_PROJECT']
    rhessys_params = os.environ['RHESSYS_PARAMS']
    # Make sure RHESSys params doesn't already contain a -pre option, if so strip it
    rhessys_params = re.sub('-pre\s+\S+\s*', '', rhessys_params)
    
    # Build RHESSys from src
    if use_src_from_data_vol:
        # Use RHESSys src from data volume
        build_dir = os.path.join(data_vol, rsrc_id, 'contents', 
                                 rhessys_project, 'rhessys', 'src', 'rhessys')
    else:
        # Use RHESSys src from src volume (i.e. Docker container)
        build_dir = os.path.join(src_vol, 'RHESSys', 'rhessys')
        
    # Make clean
    make_clean = "{0} clobber".format(MAKE_PATH)
    process = Popen(make_clean, shell=True, cwd=build_dir)
    return_code = process.wait()
    if return_code != 0:
        raise Exception("Command failed: {0}".format(make_clean))
    # Make
    process = Popen(MAKE_PATH, shell=True, cwd=build_dir)
    return_code = process.wait()
    if return_code != 0:
        raise Exception("Command failed: {0}".format(MAKE_PATH))
    
    # Find the RHESSys binary
    rhessys_bin_regex = re.compile('^rhessys.+$')
    contents = os.listdir(build_dir)
    rhessys_bin = None
    for entry in contents:
        m = rhessys_bin_regex.match(entry)
        if m:
            rhessys_bin = os.path.join(build_dir, entry)
            break
    if not rhessys_bin:
        raise Exception("Unable to find RHESSys binary in {0}".format(build_dir))
    if not os.access(rhessys_bin, os.X_OK):
        raise Exception("RHESSys binary {0} is not executable".format(rhessys_bin))

    # Run RHESSys
    rhessys_dir = os.path.join(data_vol, rsrc_id, 'contents', 
                               rhessys_project, 'rhessys')
    # Make output directory
    rhessys_out = os.path.join(rhessys_dir, 'output', run_id)
    if os.path.exists(rhessys_out):
        raise Exception("RHESSys output directory {0} already exists, and should not"
                        .format(rhessys_out))
    os.makedirs(rhessys_out, 0755)
    
    rhessys_cmd = "{0} {1} -pre output/{2}/rhessys".format(rhessys_bin, rhessys_params, run_id)
    process = Popen(rhessys_cmd, shell=True, cwd=rhessys_dir)
    return_code = process.wait()
    if return_code != 0:
        raise Exception("Command failed: {0}, cwd: {1}".format(rhessys_cmd, rhessys_dir))
    
    
if __name__ == "__main__":
    main()
    