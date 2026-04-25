import os
import asyncio
import socket
from puter import PuterAI

puter_client = None

def is_connected(timeout: float = 1.0) -> bool:
    """
    return true if the host has network connectivity.
    uses a short tcp connection to a public dns server. This is fast and doesn't perform dns lookups.
    i thought that making sure the user is online before trying to call the puter ai api would be a good idea.
    got this from https://stackoverflow.com/a/33117579, credit to user 'blhsing'.
    truth be told, i have no idea how this works.
    """
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        return True
    except OSError:
        return False

def initialize_puter_client():
    """
    initialize the puter ai client using environment variables.
    returns the client if successful, none otherwise.
    """
    global puter_client
    
    if puter_client is not None:
        return puter_client
    
    try:
        username = os.environ["PUTER_USERNAME"]
        password = os.environ["PUTER_PASSWORD"]
        puter_client = PuterAI(username=username, password=password)
        if puter_client.login():
            return puter_client
        return None
    except Exception as e:
        print(e)
        return None

def get_ai_call() -> str:
    """
    fetches a college description from puter ai api.
    uses caching to avoid duplicate api calls.
    """
    
    # initialize puter client
    client = initialize_puter_client()
    if client is None:
        return "error: puter.js credentials not set. set PUTER_USERNAME and PUTER_PASSWORD environment variables."
    
    try:
        # call puter ai to generate college description
        prompt = f"testing, tell me if I got this to work."
        description = client.chat(prompt)
        
        return description
    except Exception as e:
        # return error message if api call fails
        return f"error fetching description: {str(e)}"

print(get_ai_call())