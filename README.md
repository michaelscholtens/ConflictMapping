# Conflict Mapping Azure Function

This repo is an Azure function that automatically collects data from the Armed Conflict Location & Event Database  (ACLED) and stores it in a SQL database. This code base is in beta. However, it is fully functional and resources that rely on the connected SQL database should not expect changes to the data structure. 


## Data Schema

The function requires that a SQL database already exist to which data can be written. In most cases, this will be an Azure SQL instance. 
Ultimately, the will be three tables written to the database, an *acledEvents* table that includes the conflict events, an *actors* table that includes the unique values for actors in the ACLED dataset, and an *actorMap* table that is an adjacency list representing the initiator and target of each conflict event as the edge in a graph. 

![](/readmeMedia/Conflict%20Mapping%20Database%20Model.jpeg)

As the function is currently written, the data is update hourly. However, this can be adjusted using the Cron tabs in the function.json file. (This will be covered in more detail in the deployment instructions.) 

## Deployment Instructions

#### Setting up a Azure SQL Database

To deploy an instance of the conflict database, a Azure SQL database must be stood up on the appropriate Azure subscription for the project. 

Once this database has been created, ensure that other Azure resources are whitelisted, so that Power BI dashboards, and PowerApps can access the data. To do this, navigate to the 'Firewall Setting' tab for the database and ensure that the 'Allow access for Azure resources' toggle is switched to 'yes'. 

![](/readmeMedia/firewallSettings.PNG)

These resources have dynamic IPs, so it is vital that this option is selected when creating the database, as it is impossible to whitelist all potential IPs. (You should still whitelist your TCC computer's IP, so you can access the database to perform ad hoc analysis.) 

#### Setting up the VSCode Environment 

The easiest way to deploy an Azure web function is to use the VSCode IDE and download the Azure Functions extension. The extension can be found at the following  [link](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions). 

Once you have successfully downloaded the Azure Functions extension, clone this repository to either a local git repository or your personal github account and open the repository in VSCode. On the left, the file explorer should have the following file structure: 

![](/readmeMedia/vscodeFiles.PNG)

The first step to deploying the function is to set the global variables including the database connection string, ACLED key, email associated with the key, and country of interest. To assign these variables click on the "config.json" file in the file explorer. You should see the following file: 

![](/readmeMedia/config.PNG)

The connection string can be found in the Azure portal in the settings menu for your database. This code is written to work with the ODBC connection string, so select that option at the top of the page. It is also advised to update the string to use the most recent ODBC driver by changing "ODBC Driver 13" to "ODBC Driver 17".

![](/readmeMedia/connectionString.PNG)

For the ACLED key and email variables, the ACLED API requires authentication using a key and associated email address. The Center has a licensing agreement with ACLED allows us to use the data and there is an official key and email for this purpose. However, for fast prototyping and proof of concepts, it is possible to apply for a personal key through the ALCED website at the following [link](https://developer.acleddata.com/). 

The final variable, country, can be any country found in the ALCED dataset. The available countries can be found in the [ACLED data export tool](https://acleddata.com/data-export-tool/). As an example, a value of "Myanmar" would pull all events for Myanmar. ISO codes do not work with this script, so use the the complete name. If the country has a two word name (e.g. United States), include the space to ensure that the records match correctly. 

After the config.json file is complete, click on the function.json file in the file explorer. The file should look like the following. 

![](/readmeMedia/function.PNG)

This json file has a Cron tab under the "schedule" heading. This cron controls when the function runs. The default cron included in this repository is an hourly update that runs on the 50th minute of every hour. (i.e. 1:50). This can be changed to suit any project. The cron generator at the following [link](https://crontab.cronhub.io/) will generate six field crons that work with Azure Functions time trigger. 
