import json
import boto3
import logging
from urllib import parse
from lib.sharepoint_fn import get_sp_permissions

# initialise logger and clients
logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3_client = boto3.client('s3')
sm_client = boto3.client(service_name='secretsmanager')

# define constants
SM_SECRET_ID = 'sharepoint-connector-creds'
AUTHORITY_BASE_URL = 'https://login.microsoftonline.com/'
MSGRAPH_BASE_URL = 'https://graph.microsoft.com/v1.0'
MSGRAPH_SCOPE = ["https://graph.microsoft.com/.default"]
TARGET_S3_BUCKET = 'kendra-cde-data-bucket'


def extract_metadata_for_tags(attributes):
    s3_tags = {}
    title = ''
    category = ''
    author_str = ''
    doc_uri = ''
    doc_etag = ''
    
    for attr in attributes:
        if attr['name'] == '_document_title':
            title = attr['value']['stringValue']
        elif attr['name'] == '_category':
            category = attr['value']['stringValue']
            s3_tags['category'] = category
        elif attr['name'] == '_source_uri':
            doc_uri = attr['value']['stringValue']
            s3_tags['source_uri'] = doc_uri
        elif attr['name'] == 'sp_eTag':
            doc_etag = attr['value']['stringValue']
        elif attr['name'] == '_language_code':
            s3_tags['language'] = attr['value']['stringValue']
        elif attr['name'] == '_authors':
            # author list is in array
            author_str = ', '.join(attr['value']['stringListValue'])
            s3_tags['author'] = author_str
        elif attr['name'] == '_created_at':
            s3_tags['created_at'] = attr['value']['dateValue']
        elif attr['name'] == '_last_updated_at':
            s3_tags['last_updated_at'] = attr['value']['dateValue']
        elif attr['name'] == 'sp_modifiedBy':
            s3_tags['modified_by'] = attr['value']['stringValue']
    
    if not title:
        raise('no document title found!')
    
    return s3_tags, title, category, doc_uri, doc_etag


def lambda_handler(event, context):
    logger.info("Received event: %s" % json.dumps(event))

    # extract details from event payload
    source_s3_bucket = event.get("s3Bucket")
    source_s3_key = event.get("s3ObjectKey")
    metadata = event.get("metadata")
    # Get the document attributes from the metadata
    document_attributes = metadata.get("attributes")
    
    # read the documents
    kendra_document_object = s3_client.get_object(Bucket = source_s3_bucket, Key = source_s3_key)
    kendra_document_string = kendra_document_object['Body'].read()
    kendra_document = json.loads(kendra_document_string)
    
    # extract important metadata and construct as s3 tag
    s3_tags, doc_title, doc_category, doc_uri, doc_etag = extract_metadata_for_tags(document_attributes)

    # retrieve document permissions metadata from SharePoint and save it into a JSON file
    permissions_metadata = get_sp_permissions(logger, doc_uri, doc_etag, sm_client, SM_SECRET_ID, MSGRAPH_BASE_URL, MSGRAPH_SCOPE)
    doc_metadata = s3_tags.copy()
    doc_metadata['permissions'] = permissions_metadata
    local_file_path = f'/tmp/{doc_title}_metadata.json'
    with open(local_file_path, 'w') as outfile:
        json.dump(doc_metadata, outfile, indent=2)
    
    # upload metadata file to target S3 bucket
    permissions_file_key = 'sp_cde_output/' + doc_category + '/' + doc_title + '_permissions.json'
    s3_client.upload_file(
        local_file_path,
        TARGET_S3_BUCKET,
        permissions_file_key,
        ExtraArgs={'Tagging': parse.urlencode(s3_tags), 'ContentType': 'application/json'}
    )
        
    # write document text to tmp before uploading
    local_file_path = f'/tmp/{doc_title}.json'
    with open (local_file_path, 'w') as outfile:
        json.dump(kendra_document, outfile, indent=2)
    post_cde_key = 'sp_cde_output/' + doc_category + '/' + doc_title
    
    s3_client.upload_file(
        local_file_path,
        TARGET_S3_BUCKET,
        post_cde_key,
        ExtraArgs={'Tagging': parse.urlencode(s3_tags), 'ContentType': 'application/json'}
    )

    # optionally, delete the original file in s3
    # s3_client.delete_object(
    #     Bucket=source_s3_bucket,
    #     Key=source_s3_key
    # )

    return {
        "version" : "v0",
        "s3ObjectKey": post_cde_key,
        "metadataUpdates": []
    }
