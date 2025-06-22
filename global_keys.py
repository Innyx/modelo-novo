#import pydata_google_auth


# access / authentication
def get_api_token(choose_endpoint):
    if choose_endpoint=='PROD':
        token = 'Jzd8IiOiOhy176I1NiIsInR5cCI6IkpXVCJ1' # producao (https://semed.manaus.cloudead.com.br/bi/api/)
    elif choose_endpoint=='TEST':
         token = 'JzdWIiOiOiJIUzI1NiIsInR5cCI6IkpXVCJ9' # teste (https://ead.cloudead.com.br/bi/api/)
    #              JzdWIiOiOiJIUzI1NiIsInR5cCI6IkpXVCJ9
    else:
        token = None
    return token

def get_base_url(choose_endpoint):
    if choose_endpoint=='PROD' :
        base_url = 'https://semed.manaus.cloudead.com.br/bi/api' # producao
    elif choose_endpoint=='TEST':
        base_url = 'https://ead.cloudead.com.br/bi/api' # teste
    #elif choose_endpoint=='HML':
        #base_url = 'https://hml.semed.manaus.cloudead.com.br/bi/api' # homologacao
    #else:
        #base_url = None
    return base_url

def get_database_credentials():
    credentials = {
        "host":"db-pg-innyx-saeb.cnvnynwma1bg.sa-east-1.rds.amazonaws.com",
        "port":"5432",
        "database":"postgres",
        "user":"postgres",
        "password":"Dnoankc7BecJKEIaL1Lk"
    }
    return credentials

def get_local_database_credentials():
    credentials = {
        "host":"0.0.0.0",
        "port":"5432",
        "database":"postgres",
        "user":"luis",
        "password":"12345678"
    }
    return credentials


# def get_gbq_credentials():
#     SCOPES = [
#         'https://www.googleapis.com/auth/cloud-platform',
#         'https://www.googleapis.com/auth/drive'
#     ]
#     credentials = pydata_google_auth.get_user_credentials(
#         SCOPES,
#         auth_local_webserver=True
#     )

#     return credentials

def get_gbq_project_id():
    return 'poc-innyx-dados'