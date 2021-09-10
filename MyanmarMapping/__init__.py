import datetime
import logging

import azure.functions as func

import pandas as pd
import requests as rq
import numpy as np
import math

from urllib.parse import quote_plus
from sqlalchemy import create_engine, event
import sqlalchemy


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()


    acledKey = 'ZFU2-Xr9dvypqlvEKOHa'

    data = rq.get('https://api.acleddata.com/acled/read?key=' + acledKey + '&email=michael.scholtens@cartercenter.org&country=Myanmar&timestamp>=2021-02-01&limit=0')
    data = data.json()

    events = pd.DataFrame(data['data'])



    def sqlcol(dfparam):    
    
        dtypedict = {}
        for i,j in zip(dfparam.columns, dfparam.dtypes):
            if "object" in str(j):
                dtypedict.update({i: sqlalchemy.types.NVARCHAR(length='MAX')})
                                    
            if "datetime" in str(j):
                dtypedict.update({i: sqlalchemy.types.DateTime()})

            if "float" in str(j):
                dtypedict.update({i: sqlalchemy.types.Float(precision=3, asdecimal=True)})

            if "int" in str(j):
                dtypedict.update({i: sqlalchemy.types.Numeric()})

        return dtypedict

    #Connection String to Target Database.
    conn ='Driver={ODBC Driver 17 for SQL Server};Server=tcp:myanmarmapping.database.windows.net,1433;Database=myanmarMapping;Uid=tccuser;Pwd=2Legit2Quit;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
    quoted = quote_plus(conn)
    engine = create_engine('mssql+pyodbc:///?odbc_connect={}'.format(quoted), fast_executemany = True)

    table_name = 'acledEvents'
    
    for i in range(2):
        try:

            conn = engine.connect()

            trans = conn.begin()
            max = conn.execute('SELECT MAX(timestamp)'
                        'FROM acledEvents')
            max = max.first()[0]

            conn.close()

            acledEvents = events[events['timestamp'] > int(max)]

            types = sqlcol(acledEvents)

            acledEvents.to_sql(table_name, engine, index=False, if_exists='append', schema='dbo', chunksize = 1000, dtype = types)
            break
        except: 
            continue

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
