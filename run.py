#!/usr/bin/env python

'''
To run:

SRC_VOLUME=/tmp UUID=1345f6b3a46e RID=MYRESOURCE123 RHESSYS_PROJECT=DR5_3m_nonburned_DEM_rain_duration_DEM_float_lctest RHESSYS_PARAMS="-st 2001 1 1 1 -ed 2001 1 2 1 -b -t tecfiles/tec_daily.txt -w worldfiles/world_init -r flow/world_init_res_conn_subsurface.flow flow/world_init_res_conn_surface.flow -s 1.43092108352 3.81468111311 3.04983096856 -sv 2.35626069137 49.1712407611 -gw 0.00353233818322 0.495935816914" RHESSYS_USE_SRC_FROM_DATA=True INPUT_URL=http://127.0.0.1:8081 RESPONSE_URL=http://127.0.0.1:8080 ABORT_URL=http://127.0.0.1:8080 ./run.py
'''

import os
import sys
from subprocess import *
import re
import tempfile
import shutil
import zipfile
import StringIO
import traceback
import json
import time

import requests
from requests.exceptions import ConnectionError


MAKE_PATH = '/usr/bin/make'
BUFFER_SIZE = 10240
MAX_RETRIES = 15

def print_dir(outfile, dirname, names):
    outfile.write("Directory: {0}\n".format(dirname))
    for entry in names:
        outfile.write('\t')
        outfile.write(entry)
        outfile.write('\n')

def main():
    timestamp = str(time.time())
    debug = os.getenv('DEBUG', False)
    try:
        # Define variables referenced in exception and finally blocks
        # Create temporary directory for storing model data in
        tmp_dir = tempfile.mkdtemp()
        abort_url = None
        
        # Read environment
        abort_url = os.environ['ABORT_URL']
        src_vol = os.environ['SRC_VOLUME']
        rsrc_id = os.environ['RID']
        run_id = os.environ['UUID']
        input_url = os.environ['INPUT_URL']
        response_url = os.environ['RESPONSE_URL']
        rhessys_project = os.environ['RHESSYS_PROJECT']
        rhessys_params = os.environ['RHESSYS_PARAMS']
        if os.environ.has_key('MODEL_OPTIONS'):
            model_options = json.loads(os.environ['MODEL_OPTIONS'])
        else:
            model_options = {}
        
        bag_dir = os.path.join(tmp_dir, rsrc_id, 'bag')
        os.makedirs(bag_dir)
        tmp_zip = os.path.join(bag_dir, 'input.zip')
        
        # Download input data to temporary directory
        retries = 0
        connected = False
        while not connected:
            try:
                r = requests.get(input_url, stream=True)
                connected = True
            except ConnectionError as e:
                if retries > MAX_RETRIES:
                    raise e
                else:
                    retries += 1
                    time.sleep(13)
                    
        with open(tmp_zip, 'wb') as fd:
            for chunk in r.iter_content(BUFFER_SIZE):
                fd.write(chunk)
        
        # Unpack the bag
        bag_zip = zipfile.ZipFile(tmp_zip, 'r')
        bag_list = bag_zip.namelist()
        bag_top_level = bag_list[0].strip(os.path.sep)
        bag_zip.extractall(bag_dir)

        # Check to make sure that RHESSYS_PROJECT exits in the zipfile before extracting
        data_dir = os.path.join(bag_dir, bag_top_level, 'data', 'contents')
        zip_name = rhessys_project + os.extsep + 'zip'
        zip_path = os.path.join(data_dir, zip_name)
        zip = zipfile.ZipFile(zip_path, 'r')
        zlist = zip.namelist()
        top_level = zlist[0].strip(os.path.sep)
        if top_level != rhessys_project:
            raise Exception("Expected resource zip file to contain RHESSYS_PROJECT named {0} but found {1} at the top level of the zip file instead".format(rhessys_project, top_level))
        # Unzip input data
        zip.extractall(data_dir)
        
        # Determine which RHESSys source to use, from SRC_VOLUME or from the
        # downloaded resource
        if os.environ.has_key('RHESSYS_USE_SRC_FROM_DATA'):
            use_src_from_data_vol = bool(os.environ['RHESSYS_USE_SRC_FROM_DATA'])
        else:
            use_src_from_data_vol = False
        # Make sure RHESSys params doesn't already contain an output prefix option, 
        # if so strip it
        rhessys_params = re.sub('-pre\s+\S+\s*', '', rhessys_params)
        
        # Build RHESSys from src
        if use_src_from_data_vol:
            # Use RHESSys src from data volume
            build_dir = os.path.join(data_dir, 
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
        rhessys_dir = os.path.join(data_dir, 
                                   rhessys_project, 'rhessys')
        
        # Make sure worldfile exists
        m = re.search('-w\s+(\S+)\s*', rhessys_params)
        if not m:
            raise Exception("No worldfile defined in RHESSys parameters: {0}".format(rhessys_params))
        worldfile_path_rel = m.group(1)
        worldfile_path = os.path.join(rhessys_dir, worldfile_path_rel)
        if not os.access(worldfile_path, os.R_OK):
            raise Exception("RHESSys worldfile {0} not found in model package".format(worldfile_path_rel))        
        
        # Write TEC file if requested in MODEL_OPTIONS
        if model_options.has_key('TEC_FILE'):
            # Make sure RHESSys params doesn't already contain a tec file option, 
            # if so strip it
            rhessys_params = re.sub('-t\s+\S+\s*', '', rhessys_params)
            tec_file = timestamp
            tec_file_path_rel = os.path.join('tecfiles', tec_file)
            tec_file_path = os.path.join(rhessys_dir, tec_file_path_rel)
            tec_fp = open(tec_file_path, 'w')
            lines = model_options['TEC_FILE'].split('\\n')
            for line in lines:
                tec_fp.write(line)
                tec_fp.write('\n')
            tec_fp.close()
            rhessys_params = "{0} -t {1}".format(rhessys_params, tec_file_path_rel)
            
        # Use specific climate station if request in MODEL_OPTIONS
        if model_options.has_key('CLIMATE_STATION'):
            # Make sure climate station exists
            clim_station = "{0}.base".format(model_options['CLIMATE_STATION'])
            clim_station_path_rel = os.path.join('clim', clim_station)
            clim_station_path = os.path.join(rhessys_dir, clim_station_path_rel)
            if not os.access(clim_station_path, os.R_OK):
                raise Exception("Unable to read climate station {0}".format(clim_station_path_rel))
            
            # Look for explicit worldfile header
            input_whdr_path_rel = None
            input_whdr_path = None
            m = re.search('-whdr\s+(\S+)\s*', rhessys_params)
            if m:
                input_whdr_path_rel = m.group(1)
                input_whdr_path = os.path.join(rhessys_dir,input_whdr_path_rel)
                # Remove header
                rhessys_params = re.sub('-whdr\s+\S+\s*', '', rhessys_params)
            else:
                # Assume implicit worldfile header (we don't support old-style worldfiles
                # with embedded headers)
                input_whdr_path_rel = "{0}.hdr".format(worldfile_path_rel)
                input_whdr_path = "{0}.hdr".format(worldfile_path) 
            if not os.access(input_whdr_path, os.R_OK):
                raise Exception("Unable to read worldfile header {0}".format(input_whdr_path_rel))
            
            # Create new single-use worldfile header based on input header, changing the
            # climate station
            hdr_file = timestamp
            hdr_file_path_rel = os.path.join('worldfiles', hdr_file)
            hdr_file_path = os.path.join(rhessys_dir, hdr_file_path_rel)
            hdr_out_fp = open(hdr_file_path, 'w')
            base_station_filename_re = re.compile('^(\S+)\s+base_station_filename$')
            with open(input_whdr_path, 'r') as fp:
                for line in fp:
                    if base_station_filename_re.match(line):
                        hdr_out_fp.write("{0}\tbase_station_filename\n".format(clim_station_path_rel))
                        # Only replace first climate station found
                        break
                    else:
                        hdr_out_fp.write(line.strip() + '\n')
            hdr_out_fp.close()
            
            # Add single-use header to model command line parameters
            rhessys_params = "{0} -whdr {1}".format(rhessys_params, hdr_file_path_rel)
            
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
        
        # POST RHESSys output to RESPONSE_URL
        # Find results
        files = {}
        contents = os.listdir(rhessys_out)
        for entry in contents:
            files[entry] = open(os.path.join(rhessys_out, entry), 'rb')
        r = requests.post(response_url, files=files)
        
    except Exception as e:
        # POST error to ABORT_URL
        if abort_url:
            error_text = StringIO.StringIO()
            error_text.write(e)
            error_text.write('\n')
            error_text.write(traceback.format_exc())
            if debug:
                error_text.write('\nVolume root contents:\n')
                os.path.walk('/', print_dir, error_text)
            
            error = error_text.getvalue()
            r = requests.post(abort_url, data={"error_text" : error})
        else:
            raise e
    finally:
        # Clean up
        shutil.rmtree(tmp_dir)
            
if __name__ == "__main__":
    main()
    
