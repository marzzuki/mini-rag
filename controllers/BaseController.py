from helpers.config import get_settings
import os
import string
import secrets


class BaseController:
    def __init__(self):
        self.app_settings = get_settings()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.file_dir = os.path.join(self.base_dir, "assets", "files")

    def generate_random_string(self, length: int = 12):
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for i in range(length))
