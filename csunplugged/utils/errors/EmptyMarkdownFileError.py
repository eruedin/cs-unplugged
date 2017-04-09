from .Error import Error

class EmptyMarkdownFileError(Exception):
    """Raised when there is no content (excluding title) in a Markdown File
    """
    
    def __init__(self):
    	super().__init__()
