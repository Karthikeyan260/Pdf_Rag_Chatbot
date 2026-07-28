from app.services.pdf_processing.pipeline import process_document
from app.workers.celery_app import celery_app


@celery_app.task(name="process_document_task", bind=True, max_retries=1)
def process_document_task(self, document_id: str) -> str:
    process_document(document_id)
    return document_id
