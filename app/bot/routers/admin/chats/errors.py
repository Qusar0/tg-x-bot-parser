class ChatExistsError(Exception):
    def __init__(self, relinked: bool = False):
        self.relinked = relinked
        super().__init__()


class ChatNotExistError(Exception):
    pass
