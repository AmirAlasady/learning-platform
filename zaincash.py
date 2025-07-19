import time
import json
import requests
import jwt

# ZainCash Test Credentials
ZAINCASH_TEST_CREDENTIALS = {
    'msisdn': '9647835077893',  # Merchant phone number
    'merchant_id': '5ffacf6612b5777c6d44266f',
    'merchant_secret': '$2y$10$hBbAZo2GfSSvyqAyV2SaqOfYewgYpfR1O19gIh4SqyGWdmySZYPuS',
    'language': 'en',
    'is_production': False  # Set to True for production
}

# API URLs
TEST_API_URL = "https://test.zaincash.iq"
PRODUCTION_API_URL = "https://api.zaincash.iq"

def get_api_url():
    """Return the appropriate API URL based on environment"""
    if ZAINCASH_TEST_CREDENTIALS['is_production']:
        return PRODUCTION_API_URL
    else:
        return TEST_API_URL

def create_transaction(amount, order_id, service_type, redirect_url, credentials=None):
    """
    Create a new ZainCash transaction
    
    Args:
        amount (float): Transaction amount (must be >= 250 IQD)
        order_id (str): Your internal order reference
        service_type (str): Description of the service being purchased
        redirect_url (str): URL to redirect after payment
        credentials (dict, optional): ZainCash credentials. Defaults to test credentials.
    
    Returns:
        dict: Response from ZainCash with transaction details
    """
    if credentials is None:
        credentials = ZAINCASH_TEST_CREDENTIALS
    
    # Ensure minimum amount
    amount = max(250, float(amount))
    
    # Build request data
    data = {
        'amount': amount,
        'serviceType': service_type,
        'msisdn': credentials['msisdn'],
        'orderId': str(order_id),
        'redirectUrl': redirect_url,
        'iat': int(time.time()),
        'exp': int(time.time() + 60 * 60 * 4)  # Token valid for 4 hours
    }
    
    # Encode JWT token
    token = jwt.encode(
        data,
        credentials['merchant_secret'],
        algorithm='HS256'
    )
    
    # Prepare request data
    post_data = {
        'token': token,
        'merchantId': credentials['merchant_id'],
        'lang': credentials['language']
    }
    
    # Make request to ZainCash
    api_url = get_api_url()
    response = requests.post(
        f"{api_url}/transaction/init",
        data=post_data
    )
    
    # Parse response
    result = response.json()
    
    if 'id' in result:
        # Add payment URL to result
        result['payment_url'] = f"{api_url}/transaction/pay?id={result['id']}"
    
    return result

def verify_transaction(transaction_id, credentials=None):
    """
    Verify transaction status
    
    Args:
        transaction_id (str): ZainCash transaction ID
        credentials (dict, optional): ZainCash credentials. Defaults to test credentials.
    
    Returns:
        dict: Transaction details
    """
    if credentials is None:
        credentials = ZAINCASH_TEST_CREDENTIALS
    
    # Build request data
    data = {
        'id': transaction_id,
        'msisdn': credentials['msisdn'],
        'iat': int(time.time()),
        'exp': int(time.time() + 60 * 60 * 4)  # Token valid for 4 hours
    }
    
    # Encode JWT token
    token = jwt.encode(
        data,
        credentials['merchant_secret'],
        algorithm='HS256'
    )
    
    # Prepare request data
    post_data = {
        'token': token,
        'merchantId': credentials['merchant_id']
    }
    
    # Make request to ZainCash
    api_url = get_api_url()
    response = requests.post(
        f"{api_url}/transaction/get",
        data=post_data
    )
    
    # Parse response
    return response.json()

def decode_redirect_token(token, credentials=None):
    """
    Decode the token received from ZainCash redirect
    
    Args:
        token (str): JWT token from redirect
        credentials (dict, optional): ZainCash credentials. Defaults to test credentials.
    
    Returns:
        dict: Decoded token data
    """
    if credentials is None:
        credentials = ZAINCASH_TEST_CREDENTIALS
    
    try:
        decoded = jwt.decode(
            token, 
            credentials['merchant_secret'],
            algorithms=['HS256']
        )
        return decoded
    except Exception as e:
        return {'status': 'error', 'message': str(e)}