#!/bin/bash
# run dbbact develop website on local mac
conda activate dbbact
echo "running dbbact website server local. to access open browser to http://127.0.0.1:7000"
export DBBACT_SERVER_TYPE="develop"
export DBBACT_SERVER_PORT="7001"
export DBBACT_SERVER_HOST="0.0.0.0"
gunicorn 'dbbact_website.Server_Main:gunicorn(debug_level=2)' -b 0.0.0.0:7000 --workers 1 --name=dev-dbbact-website --timeout 300 --reload
