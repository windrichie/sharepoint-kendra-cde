import requests
import json
from botocore.exceptions import ClientError


def get_sp_credentials(client, secret_id):

    try:
        response = client.get_secret_value(
            SecretId=secret_id
        )
    except ClientError as e:
        raise e

    sp_credentials = json.loads(response['SecretString'])
    client_id = sp_credentials['client_id']
    client_secret = sp_credentials['client_secret']
    tenant_id = sp_credentials['tenant_id']

    return client_id, client_secret, tenant_id


def get_entraid_access_token(client_id, client_secret, tenant_id, scope, logger):

    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': scope
    }
    auth_url = f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'
    response = requests.post(auth_url, data=payload)
    response_json = json.loads(response.text)

    if "access_token" in response_json:
        return response_json['access_token']
    else:
        logger.info(response_json.get("error"))
        logger.info(response_json.get("error_description"))
        logger.info(response_json.get("correlation_id"))  # You may need this when reporting a bug
        return None


def call_ms_graph_api(endpoint, token):
    graph_data = requests.get(  # Use token to call downstream service
        endpoint,
        headers={'Authorization': 'Bearer ' + token}, ).json()
    
    return graph_data
    
    
def get_sp_permissions(logger, doc_uri, doc_etag, sm_client, sm_secret_id, msgraph_base_url, msgraph_scope):

    # retrieve SP credentials and generate access token
    client_id, client_secret, tenant_id = get_sp_credentials(sm_client, sm_secret_id)
    access_token = get_entraid_access_token(client_id, client_secret, tenant_id, msgraph_scope, logger)
    
    # extract site name from document URI and retrieve its site id
    site_name = doc_uri.split('/')[4]
    search_site_endpoint = f"{msgraph_base_url}/sites?search={site_name}"
    response = call_ms_graph_api(search_site_endpoint, access_token)
    site_id = response['value'][0]['id']
    # logger.info(site_id)
    
    # search item by document etag, and retrieve the item id
    get_item_id_endpoint = f"{msgraph_base_url}/sites/{site_id}/drive/items?$filter=contains(eTag, '{doc_etag}')"
    response = call_ms_graph_api(get_item_id_endpoint, access_token)
    # logger.info("\nItem details: ")
    # logger.info(json.dumps(response, indent=2))
    item_id = response['value'][0]['id']
    # item_path = response['value'][0]['parentReference']['path']
    # item_parent_id = response['value'][0]['parentReference']['id']
    # item_web_url = response['value'][0]['webUrl']
    
    # retrieve items permissions metadata
    get_item_permissions_endpoint = f"{msgraph_base_url}/sites/{site_id}/drive/items/{item_id}/permissions"
    response = call_ms_graph_api(get_item_permissions_endpoint, access_token)
    # logger.info("\nItem permissions details: ")
    # logger.info(json.dumps(response, indent=2))
    permissions_list = []
    for permission in response['value']:
        keys_to_keep = {'id', 'roles', 'grantedToV2'}
        curr_permission = {
            key: value for key, value in permission.items() if key in keys_to_keep
        }
        permissions_list.append(curr_permission)
    
    logger.info("\nItem permissions list: ")
    logger.info(json.dumps(permissions_list))
    
    return permissions_list