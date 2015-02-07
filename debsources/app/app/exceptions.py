class HTTP500Error(Exception):
    pass


class HTTP404Error(Exception):
    pass


class HTTP404ErrorSuggestions(HTTP404Error):
    def __init__(self, package, version, path):
        self.package = package
        self.version = version
        self.path = path
        super(HTTP404ErrorSuggestions, self).__init__()


class HTTP403Error(Exception):
    pass
