class OMDbError(Exception):
    """Exception class that indicates error with OMDb request based on response data."""

    def __init__(self, error: str):
        super().__init__()
        self.error = error

    def __str__(self):
        return f'OMDb request error: {self.error}'
