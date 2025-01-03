import datetime
import logging

import azure.functions as func

import pandas as pd
import requests as rq
import numpy as np
import json

from urllib.parse import quote_plus
from sqlalchemy import create_engine, event
import sqlalchemy


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    # Loading config file. 
    file = open(r'config.json',)
    config = json.load(file)
    print(config)
    print(config['country'])

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

    #This function is used to prevent overlap in PowerBI of locations geolocated to the exact same location. It will not move the location by more than 15.697 km, which is well within the geoprecision of the vast majority of ACLED data. 
    def jitter(longitude, latitude):

        delta_1 = np.random.rand(1,len(longitude))[0]/100
        delta_2 = np.random.rand(1,len(latitude))[0]/100
        newLongitude = np.add(np.array(longitude),delta_1)
        newLatitude = np.add(np.array(latitude), delta_2)

        return newLongitude, newLatitude

    #Connection String to target Database.
    conn = config['connectionString']
    quoted = quote_plus(conn)
    engine = create_engine('mssql+pyodbc:///?odbc_connect={}'.format(quoted), fast_executemany = True)

    # For loop used to ensure that connection timeouts when connecting to elastic pools do not cause a failure. Could be refactored to try/except logic, but this is fully functional.
    for i in range(2):
        try:
            #Table name for main conlfict events table 
            # table_name = 'acledEvents'
            #ACLED key for pulling data
            acledKey = config['acledKey']
            #Email address associated with ACLED key.
            email = config['email']
            #Country to pull data for.
            country = config['country']

            #API request for ACLED data. See documentation at https://acleddata.com/resources/general-guides/
            data = rq.get('https://api.acleddata.com/acled/read?key=' + acledKey + '&email='+ email + '&country='+ country +'&country_where=%3D&limit=0')
            data = data.json()

            acledEvents = pd.DataFrame(data['data'])

            print('Initial Event Count:')
            print(len(acledEvents))

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


            #To find the new actors in the ACLED dataset, we take the set of the actors previously found in the data, and 'subtract' it from the set of the new actors. 
            actorsOld = set(actors['Actors'])
            actorsNew = set(acledEvents['actor1'])
            actorsSet = list(actorsNew.difference(actorsOld))

            #The new actors are placed in a data frame
            actorsComplete = pd.DataFrame(actorsSet, columns = ['Actors'])

            #All of the new actors are assigned a label of 'Not Yet Classfied'
            actorsComplete['Classification'] = "Not Yet Classified"

            #The old list of actors and the new list of actors are combined to created the new complete list of actors.
            actorsUpdate = actors.append(actorsComplete, ignore_index = True)

            #Add index to complete data
            actorsUpdate['id'] = actorsUpdate.index
            
            #Determine datatypes
            types = sqlcol(actors)

            #Write actors table to database
            actorsUpdate.to_sql(table_name, engine, index=False, if_exists='replace', schema='dbo', chunksize = 1000, dtype = types)

            # These SQL statements are required to create a primary key for the actors table, so it can be editable by the accompanying PowerApp.
            with engine.connect() as con:
                #This first stantement constrains the id column so it is a non-nullable field, which is required in order to set it as the primary key.
                con.execute('ALTER TABLE actors ALTER COLUMN id int NOT NULL')
                #This second statment sets the id column as the primary key.
                con.execute('ALTER TABLE actors ADD PRIMARY KEY (id)')

            #This line of code creates columns in the 'acledEvents' table cased on a merge with the 'actors' table. These columns are a workaround for occlusion of the correct classifications on the map in Power BI. 
            
            classes = actorsUpdate.drop(columns=['Notes'])
            classed = acledEvents.merge(classes, left_on = 'actor1', right_on = 'Actors')

            #Write data to database
            table_name = 'acledEvents'
            types = sqlcol(classed)

            #Testing a function to jitter results to prevent occlusion. 
            newLongitude, newLatitude = jitter(pd.to_numeric(classed['longitude']), pd.to_numeric(classed['latitude']))

            classed['longitude'] = newLongitude
            classed['latitude'] = newLatitude

            classed.to_sql(table_name, engine, index=False, if_exists='replace', schema='dbo', chunksize = 1000, dtype = types)
            print('Final Event Count:')
            print(len(classed))


        except: 
            print("Failed")
            continue

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
