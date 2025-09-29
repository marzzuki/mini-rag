from enum import Enum


class LLMEnum(Enum):
    OPENAI = "OPENAI"
    COHERE = "COHERE"


class OpenAIEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class CoHereEnums(Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"

    DOCUMENT = "search_document"
    QUERY = "query"


class DocumentTypeEnum(Enum):
    DOCUMENT = "search_document"
    QUERY = "search_query"
