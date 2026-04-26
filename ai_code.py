import os
import asyncio
import socket
from puter import ChatCompletion
from typing import overload

class NodeWithParentsAlreadyExistsException(Exception):
    """
    Raised when an attempt is made to create a Node from a parent pair 
    that has already been used.
    """
    pass

class Node:
    """
    Represents a data entity that can be derived from parent nodes.
    
    Attributes:
        current_node_parents (list): Class-level registry of parent name tuples 
                                     to prevent duplicate combinations.
    """
    current_node_parents: list[tuple[str, str]] = []
    
    def __init__(self, name, sdescription=None, ldescription=None, is_user_created: bool = False, parents=None):
        """
        Initializes a Node instance.

        Args:
            name (str): The unique name of the node.
            sdescription (str, optional): Short summary. Defaults to AI generation if None.
            ldescription (str, optional): Detailed description. Defaults to None.
            is_user_created (bool): If True, skips AI generation logic.
            parents (list, optional): List of parent entities.
        """
        self.name = name
        self.parents = parents or []
        
        # Automatically generate a short description for non-user nodes if missing
        if (sdescription is None) and (not is_user_created):
            sdescription = get_short_ai_description(name)
        self.shortDescription = sdescription
        
        self.longDescription = ldescription
        self.is_user_created = is_user_created

    @staticmethod
    def make_node_from_parents(parent1: str | object, parent2: str | object):
        """
        Factory method to generate a new Node from two parents.

        Checks for existing parent combinations in both directions (A,B and B,A).

        Args:
            parent1: The first parent object or string.
            parent2: The second parent object or string.

        Returns:
            Node: A new node instance with a generated name.

        Raises:
            NodeWithParentsAlreadyExistsException: If the parent pair is already registered.
        """
        name1 = parent1.getName()
        name2 = parent2.getName()
        
        # Check global registry for existing combinations
        if (name1, name2) in Node.current_node_parents or \
            (name2, name1) in Node.current_node_parents:
            raise NodeWithParentsAlreadyExistsException(f"{name1} and {name2}")
        
        Node.add_parents_to_list(name1, name2)

        return Node(get_new_node_name(name1, name2), parents=[parent1, parent2])
    
    @staticmethod
    def add_parents_to_list(parent1: str, parent2: str) -> None:
        """
        Registers a pair of parent names into the global tracking list.
        """
        Node.current_node_parents.append((parent1, parent2))
    
    def getName(self):
        """Returns the node's name."""
        return self.name
    
    def getShortDescription(self):
        """
        Retrieves the brief description.
        Returns a static string if the node was user-created.
        """
        if self.is_user_created:
            return "You created this node"
        return self.shortDescription
    
    def getLongDescription(self) -> str | None:
        """
        Retrieves the detailed description.
        For non-user nodes, it triggers AI generation if the description is missing.
        
        Returns:
            str | None: The long description or None if it cannot be generated.
        """
        if self.longDescription != None:
            return self.longDescription
        elif not self.is_user_created:
            # Cache the AI-generated description on first access
            self.longDescription = get_long_ai_description(self.name)
            return self.longDescription
        
        return None
    
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
    """
    Sends a text prompt to the Puter AI API using the gpt-4o-mini model.
    
    The function attempts to resolve the API key in the following order:
    1. Direct argument passed to the function.
    2. 'PUTER_API_KEY' environment variable.
    3. The last non-empty line of a local '.api_key' file.

    Args:
        prompt (str): The text instructions for the AI.
        api_key (str, optional): The Puter API key.

    Returns:
        dict: The full JSON response from ChatCompletion.
    """
    if api_key == None:
        try:
            api_key = os.environ["PUTER_API_KEY"]
        except Exception:
            with open(".api_key", 'r') as f:
                for line in f:
                    api_key = line.strip()
                
    response = ChatCompletion.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        driver="openai-completion",
        api_key=api_key
    )
    return response

def get_new_node_name(idea1: str, idea2: str) -> str:
    """
    Generates a new idea name by combining two existing ideas via AI.
    
    Constraints:
        - Format: Short, simple sentence matching the phrasing of inputs.
        - Length: Maximum 15 words.
        - Style: No directive language (e.g., avoids "create a").

    Returns:
        str: The generated name or a "gulp" error message if the API call fails.
    """
    prompt = f"can you generate a new idea based off of {idea1} and {idea2} that will encourage the user to explore new ideas? make sure you return a short & simple sentence formatted in the same phrasing as the ideas. don't be too specific and limit yourself to 15 words. don't use words like \"create a\" or \"develop a\" or anything similar that prompts the user."
    name: str = prompt_puter_ai(prompt)
    if name is None or (not name["success"]):
        return f"error: uhh something went wrong. gulp."
    
    return name['result']['message']['content']

def get_short_ai_description(name: str) -> str:
    """
    Generates a 2-3 sentence summary for a given node name using AI.

    Returns:
        str: The short description or an error message.
    """
    prompt = f"can you generate a short description over {name}, make it 2-3 sentences long."
    short_description = prompt_puter_ai(prompt)
    if short_description is None or (not short_description["success"]):
        return f"error: uhh something went wrong. gulp."
    
    return short_description['result']['message']['content']

def get_long_ai_description(name: str) -> str:
    """
    Generates a high-detail, lengthy description for a given node name.

    Returns:
        str: The detailed content or an error message.
    """
    prompt = f"can you generate a description for {name} that goes into detail. feel free to make it lengthy and as detailed as possible."
    long_description = prompt_puter_ai(prompt)
    if long_description is None or (not long_description["success"]):
        return f"error: uhh something went wrong. gulp."

    return long_description['result']['message']['content']

def get_new_ai_idea_node(idea1: str, idea2: str) -> Node | str:
    """
    Orchestrates the creation of a complete Node object from two parent ideas.
    
    Workflow:
        1. Generates a name based on idea1 and idea2.
        2. Fetches both short and long AI descriptions for that name.
        3. Constructs and returns a new Node instance.

    Returns:
        Node: A fully populated Node object if successful.
        str: An error message if any part of the generation process fails.
    """
    try:
        name = get_new_node_name(idea1, idea2)
        # Note: This calls AI three times total (name, short desc, long desc)
        newNode = Node(name, get_short_ai_description(name), get_long_ai_description(name))
        return newNode
    except Exception as e:
        return f"error fetching description: {str(e)}"