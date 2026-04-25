import os
import asyncio
import socket
from puter import ChatCompletion

class Node:
    def __init__(self, name, sdescription = None, ldescription = None):
        self.name = name
        self.shortDescription = sdescription
        self.longDescription = ldescription
    
    def getName(self):
        return self.name
    
    def getShortDescription(self):
        return self.shortDescription
    
    def getLongDescription(self):
        return self.longDescription if (self.longDescription != None) else get_long_ai_description(self.name)
    
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

def prompt_puter_ai(prompt: str, api_key: str = None) -> dict[str, bool | str | list | dict[str | bool | dict]]:
    if api_key == None:
        api_key = os.environ["PUTER_API_KEY"]
    
    response = ChatCompletion.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        driver="openai-completion",
        api_key=api_key
    )
    return response

def initialize_puter_client():
    """
    DEPRECATED, USE `prompt_puter_ai` INSTEAD \n
    initialize the puter ai client using environment variables.
    returns the client if successful, none otherwise.
    """
    global puter_client
    
    if puter_client is not None:
        return puter_client
    
    try:
        api_key = os.environ["PUTER_API_KEY"]
        response = ChatCompletion.create(
            messages=[{"role": "user", "content": "how many usages do i have left"}],
            model="gpt-4o-mini",
            driver="openai-completion",
            api_key=api_key # put api key from puter.com here please
        )
        print(response)

        if response["success"]:
            return response['result']['message']['content']
        return None
    except Exception as e:
        print(e)
        return None

def get_new_node_name(idea1: str, idea2: str) -> str:
    prompt = f"can you generate a new idea based off of {idea1} and {idea2} that will encourage the user to explore new ideas? make sure you return a simple sentence formatted in the same phrasing as the ideas. don't be too specific and limit yourself to 15 words."
    name: str = prompt_puter_ai(prompt)
    if name is None or (not name["success"]):
        return f"error: uhh something went wrong. gulp."
    
    return name['result']['message']['content']

def get_short_ai_description(name: str) -> str:
    prompt = f"can you generate a short description over {name}, make it 2-3 sentences long."
    short_description = prompt_puter_ai(prompt)
    if short_description is None or (not short_description["success"]):
        return f"error: uhh something went wrong. gulp."
    
    return short_description['result']['message']['content']

def get_long_ai_description(name: str) -> Node:
    prompt = f"can you generate a description for {name} that goes into detail. feel free to make it lengthy and as detailed as possible."
    long_description = prompt_puter_ai(prompt)
    if long_description is None or (not long_description["success"]):
        return f"error: uhh something went wrong. gulp."

    return long_description['result']['message']['content']

def get_new_ai_idea_node(idea1: str, idea2: str) -> str:
    """
    fetches a new idea node from puter ai api.
    """
    
    try:
        name = get_new_node_name(idea1, idea2)
        newNode = Node(name, get_short_ai_description(name), get_long_ai_description(name))
        return newNode
    except Exception as e:
        # return error message if api call fails
        return f"error fetching description: {str(e)}"

newNode = get_new_ai_idea_node("learning physics", "making a game in godot")

print(newNode.getName())
print(newNode.getShortDescription())
print("\n\n\n")
print(newNode.getLongDescription())