# Using Kendra Custom Document Enrichment (CDE) to extract permissions metadata from SharePoint

This repository provides sample Lambda function code that can be used as Kendra CDE Post-Extraction Advanced Operations. The code extracts additional metadata, including document permissions metadata from SharePoint using Microsoft Graph APIs.

## Disclaimer
This project is used for demo purposes only and should NOT be considered for production use.

## Pre-requisites

1. Create an [App Registration](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app) in Microsoft Entra ID. This can be the same app registration that you have created as part of the Kendra SharePoint v2 connector setup. For details on what permissions to provide to the app, you can refer to [our Kendra documentation](https://docs.aws.amazon.com/kendra/latest/dg/data-source-v2-sharepoint.html)

1. Once created, take note of the tenant id and client id. Then, create a secret under `Certificates & secrets` tab in Microsoft Entra ID.

1. Create an AWS Secret Manager secret called `sharepoint-connector-creds` with the following details:
    ```json
    {
        "tenant_id": "<Microsoft Entra ID Tenant ID>",
        "client_id": "<Client ID of App Registration>",
        "client_secret": "<Value of the created Secret>"
    }
    ```

1. Create a SharePoint data source in Kendra. See [this documentation](https://docs.aws.amazon.com/kendra/latest/dg/data-source-v2-sharepoint.html) for more details.

## Deployment Steps

1. Create a Lambda execution role with the following minimum permissions:
    - Read permissions to the above secret
    - S3 read, write and delete permissions to the Kendra CDE bucket

1. Create a Lambda function with the code provided in this repository (including the `lib/` folder as well), with the above execution role.

1. Enable Kendra CDE and use the Lambda function as the post-extraction Lambda function. See [this documentation](https://docs.aws.amazon.com/kendra/latest/dg/custom-document-enrichment.html#advanced-data-manipulation) and [this blog post](https://aws.amazon.com/blogs/machine-learning/enrich-your-content-and-metadata-to-enhance-your-search-experience-with-custom-document-enrichment-in-amazon-kendra/) for more information.

1. Ensure that the CDE is assigned to the Kendra SharePoint data source that you have created. Trigger the sync of the connector to test the CDE.