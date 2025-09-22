from .BaseController import BaseController
from .ProjectController import ProjectController
from models import ResponseMessage
import re
import os


class FileController(BaseController):
    def __init__(self):
        super().__init__()
        self.size_scale = 1048576  # MB to Byte

    def validate_uploaded_file(self, file: str):
        if file.content_type not in self.app_settings.FILE_ALLOWED_EXTENSIONS:
            return False, ResponseMessage.FILE_TYPE_NOT_SUPPORTED.value

        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False, ResponseMessage.FILE_SIZE_EXCEEDED.value

        return True, ResponseMessage.FILE_VALIDATED_SUCCESS.value

    def get_clean_file_name(self, orig_file_name: str):
        return re.sub(r"[^\w.]", "", orig_file_name.strip()).replace(" ", "_")

    def generate_unique_filename(self, orig_file_name: str, project_id: str):
        random_key = self.generate_random_string()
        project_path = ProjectController().get_project_path(project_id=project_id)

        cleaned_file_name = self.get_clean_file_name(orig_file_name=orig_file_name)
        new_file_path = os.path.join(project_path, random_key + "_" + cleaned_file_name)

        while os.path.exists(new_file_path):
            random_key = self.generate_random_string()
            new_file_path = os.path.join(
                project_path, random_key + "_" + cleaned_file_name
            )

        return new_file_path, random_key + "_" + cleaned_file_name
