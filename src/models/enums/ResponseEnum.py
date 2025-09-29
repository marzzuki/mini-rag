from enum import Enum


class ResponseMessageEnum(Enum):
    FILE_VALIDATED_SUCCESS = "file_validate_successfully"
    FILE_TYPE_NOT_SUPPORTED = "file_type_not_supported"
    FILE_SIZE_EXCEEDED = "file_size_exceeded"
    FILE_UPLOAD_SUCCESS = "file_upload_success"
    FILE_UPLOAD_FAILED = "file_upload_failed"
    FILE_PROCESS_FAILED = "file_processing_failed"
    FILE_PROCESS_SUCCESS = "file_processing_success"
    NO_FILES_ERROR = "no_file_found"
    FILE_ID_ERROR = "no_file_found_with_this_id"
    PROJECT_NOT_FOUND_ERROR = "project_was_not_found"
    INSERT_INTO_VECTORDB_ERROR = "error_while_inserting_into_vedctordb"
    INSERT_INTO_VECTORDB_SUCCESS = "inserted_into_vedctordb_success"
    VECTORDB_COLLECTION_RETRIEVED_SUCCESS = "vectordb_collection_retreive_success"
    VECTORDB_SEARCH_ERROR = "vectordb_search_error"
    VECTORDB_SEARCH_SUCCESS = "vectordb_search_success"
