RHESSys_docker
==============

Configuration for running HydroShare RHESSysWorkflows models in Docker containers


Running RHESSys
---------------

The run.py executable should be used to run RHESSys.  This requires that the following
environment variables be set in your container:

- SRC_VOLUME: The mount point in the Docker container where the RHESSys_docker repo has 
been cloned
- DATA_VOLUME: The mount point in the Docker container where the RHESSysWorkflows project 
is accessible
- RID: The HydroShare resource ID of the RHESSysWorkflows resource
- UUID: A one-time key to be used for posting model results to HydroShare
- RESULTS_URL: The HydroShare resource URL where results should be posted to
- RHESSYS_PROJECT: The name of the RHESSysWorkflows project directory
- RHESSYS_PARAMS: The command line parameters used to run RHESSys

Optionally, the following environment variables can be set:

- RHESSYS_USE_SRC_FROM_DATA: [True | False].  If True, RHESSys source code will be 
compiled from the RHESSysWorkflows project instead of from the RHESSys_docker repo.

Testing
-------

It is possible to test the run.py executable outside of Docker.  To do so, start up
the provided test_server.py, and run run.py, for example:

    SRC_VOLUME=/tmp DATA_VOLUME=/tmp UUID=1345f6b3a46e RID=MYRESOURCE123 RHESSYS_PROJECT=DR5_3m_nonburned_DEM_rain_duration_DEM_float_lctest RHESSYS_PARAMS="-st 2001 1 1 1 -ed 2001 1 2 1 -b -t tecfiles/tec_daily.txt -w worldfiles/world_init -r flow/world_init_res_conn_subsurface.flow flow/world_init_res_conn_surface.flow -s 1.43092108352 3.81468111311 3.04983096856 -sv 2.35626069137 49.1712407611 -gw 0.00353233818322 0.495935816914" RHESSYS_USE_SRC_FROM_DATA=True RESULTS_URL=http://127.0.0.1:8080 ./run.py
