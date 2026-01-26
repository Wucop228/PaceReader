from app.core.base_dao import BaseDAO
from app.text.models import Document, Summary


class DocumentDAO(BaseDAO):
    model = Document


class SummaryDAO(BaseDAO):
    model = Summary