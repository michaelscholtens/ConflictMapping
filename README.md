# Getting Started

The easiest way to deploy an Azure web function is to use the VSCode IDE and download the Azure Functions extension. The extension can be found at the following  [link](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions). 


## Data Schema

The function requires that a SQL database already exist to which data can be written. In most instances this will be an Azure SQL instance. 
Ultimately, the will be three tables written to the database, an *acledEvents* table that includes the conflict events, an *actors* table that includes the unique values for actors in the ACLED dataset, and an *actorMap* table that is an adjacency list representing the initiator and target of each conflict event as the edge in a graph. 
