#!/bin/bash
# run dbbact develop website on local mac
conda activate dbbact
export DBBACT_SERVER_PORT="7001"
export DBBACT_WEBSITE_PORT="5001"
echo "running dbbact website server local. to access open browser to http://127.0.0.1:$DBBACT_WEBSITE_PORT"
export DBBACT_SERVER_TYPE="develop"
export DBBACT_SERVER_HOST="0.0.0.0"
export CALOUR_CONFIG_FILE="calour.config.local"
gunicorn 'dbbact_website.Server_Main:gunicorn(debug_level=2)' -b 0.0.0.0:$DBBACT_WEBSITE_PORT --workers 1 --name=dev-dbbact-website --timeout 300 --reload
