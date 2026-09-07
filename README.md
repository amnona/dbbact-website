![image](https://github.com/amnona/dbbact-website/assets/5832946/1299f9e2-4df6-45c2-b953-26cb2e921b41)

# dbbact-website
This is the code for the website (http) server for [dbBact](https://dbbact.org), the open microbiome knowledge base.

For more details about dbBact, see [Nucleic Acids Research 2023](https://doi.org/10.1093/nar/gkad527) paper.

The dbBact support forum is now live at: [dbbact.boards.net](https://dbbact.boards.net/)

## Installation
dbBact-website requires the [dbBact-server](https://github.com/amnona/dbbact-server) server to be installed and running.

To install dbBact-website, clone this repository and install the required Python packages:

```bash
git clone https://github.com/amnona/dbbact-website.git
cd dbbact-website
pip install -e .
```

## Running

To run the dbBact-website server, use the following command:

```bash
cd dbbact-website
run_server_local.sh
```

By default, the server will run in develop mode and be accessible at [http://127.0.0.1:7001](http://127.0.0.1:7001).
