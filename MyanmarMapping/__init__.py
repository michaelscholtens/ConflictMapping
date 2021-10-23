import datetime
import logging

import azure.functions as func

import pandas as pd
import requests as rq
import numpy as np
import time

from urllib.parse import quote_plus
from sqlalchemy import create_engine, event
import sqlalchemy


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    #Function used to ensure data types are stored correctly on ingestion to the SQL database.
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

    #Connection String to target Database.
    conn ='Driver={ODBC Driver 17 for SQL Server};Server=tcp:myanmarmapping.database.windows.net,1433;Database=myanmarMapping;Uid=tccuser;Pwd=2Legit2Quit;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'
    quoted = quote_plus(conn)
    engine = create_engine('mssql+pyodbc:///?odbc_connect={}'.format(quoted), fast_executemany = True)

    # For loop used to ensure that connection timeouts when connecting to elastic pools do not cause a failure. Could be refactored to try/except logic, but this is fully functional.
    for i in range(2):
        try:
            #Table name for main conlfict events table 
            table_name = 'acledEvents'
            #ACLED key for pulling data
            acledKey = 'ZFU2-Xr9dvypqlvEKOHa'

            #API request for ACLED data. See documentation at https://acleddata.com/resources/general-guides/
            data = rq.get('https://api.acleddata.com/acled/read?key=' + acledKey + '&email=michael.scholtens@cartercenter.org&country=Myanmar&timestamp>=2021-02-01&limit=0')
            data = data.json()

            acledEvents = pd.DataFrame(data['data'])

            types = sqlcol(acledEvents)

            #Write data to database
            acledEvents.to_sql(table_name, engine, index=False, if_exists='replace', schema='dbo', chunksize = 1000, dtype = types)


            #This next section of code produces the adjecency list for the 'Shape of Conflict' page of the Power Bi Dashboard.
            actorMap = pd.DataFrame()
            id = []
            s = []
            t = []
            d = []

            for row in acledEvents.iterrows():
                id.append(row[1]['data_id'])
                s.append(row[1]['actor1'])
                t.append(row[1]['actor2'])
                d.append(row[1]['event_date'])
                
            actorMap['data_id'] = id
            actorMap['date'] = d
            actorMap['source'] = s
            actorMap['target'] = t

            actorMap = actorMap[actorMap['date']>='2021-02-01']

            actorMap = actorMap[actorMap['target'] != '']

            table_name = 'actorMap'

            types = sqlcol(actorMap)

            actorMap['date'] =  pd.to_datetime(actorMap['date'], format='%Y-%m-%d')

            #Write the adjacency list to the database
            actorMap.to_sql(table_name, engine, index=False, if_exists='replace', schema='dbo', chunksize = 1000, dtype = types)

            table_name = 'actors'

            #This section of code reads the actors table from the database and identifies new actors from the new conflcit events and adds them to the table with the class "Not Yet Classified"
            actors = pd.read_sql(table_name, engine)

            actorsClass = set(actors['Actors'])
            actorsOld = set(acledEvents['actor1'])
            actorsNew = list(actorsClass.symmetric_difference(actorsOld))

            actorsComplete = pd.DataFrame(actorsNew, columns = ['Actors'])

            actorsComplete['Classification'] = "Not Yet Classified"

            actorsUpdate = actors.append(actorsComplete, ignore_index = True)
            
            #Some records are being duplicated, so this solves this behavior. However, this requires debugging.
            actorsUpdate.drop_duplicates(inplace = True)

            #Write actors table to database
            actorsUpdate.to_sql(table_name, engine, index=False, if_exists='replace', schema='dbo', chunksize = 1000)


        except: 
            print("Failed")
            continue

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
