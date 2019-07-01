from flask import Flask

ENV = "PROD"
### DEVELOPMENT ###
DEV_DB_USERNAME = 'papxsavx'
DEV_DB_USERNAME_PASSWORD = 'apE4-BiD1W2926_F1cPt7IrWUmm5yxXD'
DEV_DB_NAME = 'abzlwldv'
DEV_DB_HOST = 'manny.db.elephantsql.com'
DEV_DB_PORT = 5432
DEV_DB_SSL = "require"
DEV_DB_CERT_FILE = None

### PRODUCTION ###
PROD_DEBUG = False
PROD_DB_USERNAME = 'analytics'
PROD_DB_USERNAME_PASSWORD = 'LNGhuDLE*K5H5$r'
PROD_DB_NAME = 'analyticsdb'
PROD_DB_HOST = 'analytics-1-psql.c77yghrkvmqq.eu-west-1.rds.amazonaws.com'
PROD_DB_PORT = 5432
PROD_DB_SSL = 'require'


app = Flask(__name__)
